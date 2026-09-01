#!/usr/bin/env python3
"""Run HIST_SIM reference fitting across real OpenD daily histories.

The script stores only derived match metadata and an OHLC content hash; it does
not redistribute raw market data. It is an opt-in integration test because CI
does not have the user's OpenD connection or quote permissions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_SYMBOLS = (
    "US.QCOM",
    "US.TTWO",
    "US.ORCL",
    "US.AAPL",
    "US.NVDA",
    "US.TSLA",
    "US.SPY",
    "US.QQQ",
)


@dataclass(frozen=True)
class FitResult:
    mode: str
    selected_anchor_age: int
    source_start: str
    source_anchor: str
    source_end: str
    fit_score: float
    distance: float
    realized_projection_return_pct: float
    projected_bullish: bool


def fit_reference(
    frame: pd.DataFrame,
    *,
    mode: str,
    lookback: int = 50,
    projection: int = 20,
    search_history: int = 2520,
    recent_bars: int = 10,
    recent_weight: float = 1.0,
    shock_weight: float = 2.0,
) -> tuple[FitResult, int]:
    close = frame["close"].to_numpy(dtype=float)
    n = len(close)
    minimum_age = lookback + projection + 1
    max_age = min(search_history, n - lookback)
    if max_age < minimum_age:
        raise ValueError(f"only {n} bars; no complete candidate window")

    current_end = n - 1
    current_window = close[current_end - lookback + 1 : current_end + 1]
    current_start = current_window[0]
    current_last_return = math.log(close[-1] / close[-2]) * 100.0 if mode == "log" else (close[-1] / close[-2] - 1.0) * 100.0

    if mode == "log":
        current_feature = np.log(current_window / current_start) * 100.0
    else:
        current_feature = (current_window / current_start - 1.0) * 100.0

    best: tuple[float, float, int] | None = None
    candidate_count = 0
    weight_total = 1.0 + recent_weight + shock_weight

    for age in range(minimum_age, max_age + 1):
        anchor = current_end - age
        start = anchor - lookback + 1
        end_projection = anchor + projection
        if start < 0 or end_projection >= n:
            continue
        window = close[start : anchor + 1]
        if np.any(~np.isfinite(window)) or np.any(window <= 0):
            continue
        candidate_count += 1
        if mode == "log":
            historical_feature = np.log(window / window[0]) * 100.0
            historical_last_return = math.log(close[anchor] / close[anchor - 1]) * 100.0
        else:
            historical_feature = (window / window[0] - 1.0) * 100.0
            historical_last_return = (close[anchor] / close[anchor - 1] - 1.0) * 100.0

        errors = np.square(current_feature - historical_feature)
        full_mse = float(np.mean(errors))
        tail_mse = float(np.mean(errors[-recent_bars:]))
        shock_error = float((current_last_return - historical_last_return) ** 2)
        distance = full_mse + recent_weight * tail_mse + shock_weight * shock_error

        full_similarity = 100.0 / (1.0 + full_mse / 25.0)
        tail_similarity = 100.0 / (1.0 + tail_mse / 16.0)
        shock_similarity = 100.0 / (1.0 + shock_error / 4.0)
        fit_score = (full_similarity + recent_weight * tail_similarity + shock_weight * shock_similarity) / weight_total

        # Native llv_bars selects the closest bar when the minimum is tied.
        ordering = (distance, age)
        if best is None or ordering < (best[0], best[2]):
            best = (distance, fit_score, age)

    if best is None:
        raise ValueError("no valid historical candidate")

    distance, fit_score, age = best
    anchor = current_end - age
    start = anchor - lookback + 1
    end_projection = anchor + projection
    projection_return = (close[end_projection] / close[anchor] - 1.0) * 100.0
    dates = frame["time_key"].str.slice(0, 10).tolist()
    return (
        FitResult(
            mode=mode,
            selected_anchor_age=age,
            source_start=dates[start],
            source_anchor=dates[anchor],
            source_end=dates[end_projection],
            fit_score=round(fit_score, 6),
            distance=round(distance, 8),
            realized_projection_return_pct=round(projection_return, 6),
            projected_bullish=bool(projection_return >= 0),
        ),
        candidate_count,
    )


def fetch_history(ctx, code: str, start: str, end: str) -> pd.DataFrame:
    from moomoo import AuType, KLType, RET_OK

    pages: list[pd.DataFrame] = []
    page_key = None
    while True:
        ret, data, page_key = ctx.request_history_kline(
            code,
            start=start,
            end=end,
            ktype=KLType.K_DAY,
            autype=AuType.QFQ,
            max_count=1000,
            page_req_key=page_key,
        )
        if ret != RET_OK:
            raise RuntimeError(f"{code}: {data}")
        pages.append(data[["code", "time_key", "open", "close", "high", "low"]])
        if page_key is None:
            break
    frame = pd.concat(pages, ignore_index=True).drop_duplicates("time_key").sort_values("time_key").reset_index(drop=True)
    return frame


def data_hash(frame: pd.DataFrame) -> str:
    digest = hashlib.sha256()
    for row in frame.itertuples(index=False):
        digest.update(f"{row.time_key[:10]}|{row.open:.8f}|{row.high:.8f}|{row.low:.8f}|{row.close:.8f}\n".encode())
    return digest.hexdigest()


def render_markdown(payload: dict) -> str:
    lines = [
        "# HIST_SIM v2.0.1 multi-symbol regression",
        "",
        f"- Generated: {payload['generated_at']}",
        f"- Source: {payload['source']}",
        f"- Window: {payload['start']} through {payload['end']}",
        "- Data: forward-adjusted daily K-lines; raw OHLC is not redistributed",
        "",
        "| Symbol | Bars | Full 10Y | Log anchor | Log fit | 20-bar realized | Pct anchor | Pct fit |",
        "|---|---:|---|---|---:|---:|---|---:|",
    ]
    for item in payload["symbols"]:
        log = item["log"]
        pct = item["pct"]
        lines.append(
            f"| `{item['code']}` | {item['loaded_bars']} | {'PASS' if item['full_history_loaded'] else 'SHORT'} | "
            f"{log['source_anchor']} | {log['fit_score']:.2f} | {log['realized_projection_return_pct']:+.2f}% | "
            f"{pct['source_anchor']} | {pct['fit_score']:.2f} |"
        )
    lines.extend(
        [
            "",
            "Fit scores are path-similarity diagnostics, not forecast probabilities. Committed results contain only derived metadata and data hashes.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--start", default="2015-07-01")
    parser.add_argument("--end", default="2026-08-31")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=11111)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()

    from moomoo import OpenQuoteContext

    ctx = OpenQuoteContext(host=args.host, port=args.port)
    results = []
    try:
        for code in args.symbols:
            frame = fetch_history(ctx, code, args.start, args.end)
            log_result, log_candidates = fit_reference(frame, mode="log")
            pct_result, pct_candidates = fit_reference(frame, mode="pct")
            if log_candidates != pct_candidates:
                raise AssertionError(f"{code}: candidate counts differ")
            results.append(
                {
                    "code": code,
                    "loaded_bars": len(frame),
                    "first_bar": frame.iloc[0].time_key[:10],
                    "last_bar": frame.iloc[-1].time_key[:10],
                    "candidate_count": log_candidates,
                    "full_history_loaded": len(frame) >= 2570,
                    "ohlc_sha256": data_hash(frame),
                    "log": asdict(log_result),
                    "pct": asdict(pct_result),
                }
            )
    finally:
        ctx.close()

    payload = {
        "schema": 1,
        "generated_at": date.today().isoformat(),
        "source": "moomoo OpenD request_history_kline, AuType.QFQ, KLType.K_DAY",
        "start": args.start,
        "end": args.end,
        "parameters": {
            "lookback": 50,
            "projection": 20,
            "search_history": 2520,
            "recent_bars": 10,
            "recent_weight": 1.0,
            "shock_weight": 2.0,
        },
        "symbols": results,
    }

    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown(payload), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
