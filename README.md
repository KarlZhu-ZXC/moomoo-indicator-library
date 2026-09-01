# moomoo Indicator Library

<p align="center">
  <strong>Memory-bounded technical-analysis indicators for the moomoo Python custom-indicator runtime</strong><br>
  Smart Money Concepts · ChartPrime Optimal Trade Entry · Historical Similarity Projection
</p>

<p align="center">
  <img alt="Library 4.2" src="https://img.shields.io/badge/library-4.2-089981?style=for-the-badge">
  <img alt="moomoo" src="https://img.shields.io/badge/platform-moomoo-00C805?style=for-the-badge">
  <img alt="Python" src="https://img.shields.io/badge/language-Python-3178C6?style=for-the-badge">
  <img alt="Multi-license" src="https://img.shields.io/badge/license-multi--license-F23645?style=for-the-badge">
</p>

> [!IMPORTANT]
> These are unofficial community ports for education, research, and chart analysis—not automatic trading. The moomoo Desktop client remains the authoritative compiler and renderer.

## Indicator catalog

| Collection | Indicators | Version | Plot budget | Description |
|---|---|---:|---:|---|
| [Smart Money Concepts](indicators/smc/) | `SMC_STR` | 4.1 | 28 / 50 | Structure, BOS/CHoCH, swing points, EQH/EQL, Strong/Weak |
| [Smart Money Concepts](indicators/smc/) | `SMC_OB` | 4.1 | 46 / 50 | Internal/swing Order Blocks with mitigation and labels |
| [Smart Money Concepts](indicators/smc/) | `SMC_IMB` | 4.1 | 31 / 50 | FVGs and Premium/Equilibrium/Discount |
| [Optimal Trade Entry](indicators/ote/) | `OTE_CP` | 4.1 | 45 / 50 | ChartPrime-style Fibonacci grid, shifts, anchors, OTE and optional previous sets |
| [Historical Similarity](indicators/historical-similarity/) | `HIST_SIM` | 2.0.1 | 28 / 50 | Exhaustive ten-year log/percent path matching and realized continuation |
| [Historical Similarity](indicators/historical-similarity/) | `HIST_SIM_PCT` | 2.0.1 | 28 / 50 | Percentage-only compatibility fallback |

## Quick installation

Create each file as a separate **Python overlay indicator** in moomoo Desktop:

| Short name | File |
|---|---|
| `OTE_CP` | [`indicators/ote/OTE_CP.py`](indicators/ote/OTE_CP.py) |
| `SMC_STR` | [`indicators/smc/SMC_STR.py`](indicators/smc/SMC_STR.py) |
| `SMC_OB` | [`indicators/smc/SMC_OB.py`](indicators/smc/SMC_OB.py) |
| `SMC_IMB` | [`indicators/smc/SMC_IMB.py`](indicators/smc/SMC_IMB.py) |
| `HIST_SIM` | [`indicators/historical-similarity/HIST_SIM.py`](indicators/historical-similarity/HIST_SIM.py) |
| `HIST_SIM` fallback | [`indicators/historical-similarity/HIST_SIM_PCT.py`](indicators/historical-similarity/HIST_SIM_PCT.py) |

Remove older same-name indicators before loading v4.1. If the chart previously loaded a pre-v4 deep-graph build, fully quit and reopen moomoo once to clear the old indicator instance.

## What changed in v4.1

### Memory architecture

The former implementations built hundreds-deep `ref → compare → iff` Sequence graphs. v4.1 removes every 500/501-layer full-history construction loop and prefers masked native `HHV/LLV` nodes.

- `SMC_STR`: current trailing extremes use one bounded native rolling node.
- `SMC_OB`: 32 interleaved candidate lanes and 20 bounded state slots per family.
- `SMC_IMB`: 20 FVG state slots with in-place age ranking.
- `OTE_CP`: current shift masks and native confirmed-pivot extremes; previous Fib state is skipped when disabled.

Client observation from the source conversation: fast symbol switching now peaks around 2–3 GB and shows clear reclamation instead of unbounded growth.

### Fidelity fixes

- OTE simultaneous HH/LL confirmation preserves both events; bearish wins final state because its branch runs second, matching the reference execution order.
- EQH/EQL label y-position uses the newly confirmed equal pivot, not the average of both pivots.
- Default Structure label gaps increased to `0.40 / 0.50 / 0.40 / 0.40 ATR`.
- `OTE_CP` adds fixed `SH`/`SL` text beside confirmed swing markers.
- Fib styling is lighter and the OTE zone uses a pale-yellow fill.

See [v4.1 release notes](docs/releases/V4_1_CN.md) and the [import/provenance audit](docs/releases/V4_1_PROVENANCE.md).

## OTE_CP defaults

- `Pivot Length = 10`
- `Show Previous Fibs = False`
- current Fibonacci grid and swing diagonal enabled
- pale-yellow 0.618–0.786 OTE zone
- HH/LL shifts plus SH/SL swing markers

Use the same Pivot Length on TradingView and moomoo when comparing anchors. moomoo cannot reproduce Pine's dynamic numeric label strings; current prices remain available through the legend, hover values, and output parameters.

## Historical Similarity Projection

`HIST_SIM` compares the latest normalized 50-bar path against every eligible historical anchor from 71 to 2520 bars ago. On a sufficiently loaded daily chart, that is approximately 2,450 candidate windows over ten trading years.

- primary mode: cumulative natural-log path using `math_log()`;
- fallback: cumulative percentage path with no logarithm dependency;
- recent-tail and final-bar shock weighting;
- dashed matched history plus solid realized continuation;
- dynamic source dates rendered through fixed digit channels;
- explicit loaded-history and full-ten-year outputs.

The fit score is a custom similarity diagnostic, not a forecast probability. See the [collection documentation](indicators/historical-similarity/README.md), [eight-symbol OpenD regression](docs/releases/HIST_SIM_V2_0_1_REGRESSION.md), and [import audit](docs/releases/HIST_SIM_V2_0_1_PROVENANCE.md).

## Smart Money Concepts

<p align="center">
  <img src="docs/smc/assets/fig1_structure.png" alt="Market structure, BOS, and CHoCH diagram" width="900">
</p>

| Liquidity · EQH/EQL | Order Blocks · FVG |
|---|---|
| ![Liquidity](docs/smc/assets/fig2_liquidity.png) | ![Order Blocks and FVG](docs/smc/assets/fig3_ob_fvg.png) |

SMC resources:

- [Collection overview](indicators/smc/README.md)
- [Compatibility matrix](docs/smc/COMPATIBILITY.md)
- [Chinese handbook — Markdown](docs/smc/Smart_Money_Concepts_实战手册_CN.md)
- [Chinese handbook — PDF](docs/smc/Smart_Money_Concepts_实战手册_CN.pdf)

## Validation

The repository checks:

- Python syntax and global-scope plot calls;
- 50-call plot ceiling and 25-character plot names;
- tested unsupported global functions;
- absence of `Sequence.values[-1]` access;
- absence of 500/501-layer Sequence construction scans;
- deterministic simulated execution on 1,400 OHLC bars;
- LuxAlgo structure state against a scalar reference;
- ChartPrime pivot/shift/anchor state against a scalar reference;
- randomized OB selection and active-slot ranking;
- v4.1 OTE/EQH/OB fidelity regressions.
- HIST_SIM and percentage fallback simulated execution;
- exhaustive candidate-count invariants and an eight-symbol ten-year OpenD regression snapshot.

```bash
python -m pip install -r tools/reference/v4_1/requirements.txt
python tools/validate.py
python tools/reference/v4_1/validate_stub_runtime.py
python tools/reference/v4_1/validate_optimized_algorithms.py
python tools/reference/v4_1/validate_smc_reference.py
python tools/reference/v4_1/validate_ote_reference.py
python tools/reference/v4_1/validate_v4_1_fidelity.py
python -m unittest discover -s tools/tests
```

## Platform boundaries

- No verified equivalent of Pine `request.security()` for arbitrary-timeframe FVGs.
- No dynamic Pine line/box/label object lifecycle; future-space extension and large historical object sets use bounded visual equivalents.
- `plot_text()` cannot accept per-bar dynamic strings such as `0.618 (215.21)`.
- Precise trailing, OB, and anchor searches are bounded to the latest 500 bars to prevent deep graph regressions.
- HIST_SIM can search only the bars supplied by the client; check `full_history_loaded` before describing a result as ten-year coverage.

## Attribution and licenses

- `indicators/smc/*`: adapted from **Smart Money Concepts (SMC) [LuxAlgo]**, © LuxAlgo, under CC BY-NC-SA 4.0.
- `indicators/ote/OTE_CP.py`: port of **Smart Money Fibonacci OTE Engine [ChartPrime]**, preserving its MPL-2.0 attribution.
- `indicators/historical-similarity/*`: original repository contribution under CC BY-NC-SA 4.0.
- Original repository documentation and diagrams: CC BY-NC-SA 4.0 unless stated otherwise.

See [NOTICE.md](NOTICE.md), [LICENSE](LICENSE), and the [OTE license notice](indicators/ote/LICENSE.md). LuxAlgo, ChartPrime, TradingView, moomoo, and Futu names and trademarks belong to their respective owners. This project is not affiliated with, endorsed by, or sponsored by any of them.

## Risk disclosure

Indicators organize historical OHLC observations. They do not identify institutional orders, predict outcomes, define personal suitability, or replace a complete trade plan. Independently define direction, confirmation, loss boundary, target, and acceptable risk/reward before any proposed exposure.
