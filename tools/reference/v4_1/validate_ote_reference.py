from __future__ import annotations

import numpy as np
import pandas as pd


def rolling_max(a: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(a).rolling(n, min_periods=1).max().to_numpy()


def rolling_min(a: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(a).rolling(n, min_periods=1).min().to_numpy()


def ffill_event(event: np.ndarray, value: np.ndarray) -> np.ndarray:
    return pd.Series(np.where(event, value, np.nan)).ffill().to_numpy()


def vector_engine(high: np.ndarray, low: np.ndarray, n: int):
    m = len(high)
    window = n * 2 + 1
    cand_h = np.full(m, np.nan)
    cand_l = np.full(m, np.nan)
    cand_h[n:] = high[:-n]
    cand_l[n:] = low[:-n]
    ph = (np.arange(m) + 1 > window) & np.isclose(cand_h, rolling_max(high, window), rtol=0, atol=0)
    pl = (np.arange(m) + 1 > window) & np.isclose(cand_l, rolling_min(low, window), rtol=0, atol=0)

    last_h = ffill_event(ph, cand_h)
    last_l = ffill_event(pl, cand_l)
    prev_h = np.r_[np.nan, last_h[:-1]]
    prev_l = np.r_[np.nan, last_l[:-1]]
    hh = ph & ~np.isnan(prev_h) & (cand_h > prev_h)
    ll = pl & ~np.isnan(prev_l) & (cand_l < prev_l)
    raw = hh | ll
    raw_dir = np.where(ll, -1.0, np.where(hh, 1.0, np.nan))
    last_raw_dir = ffill_event(raw, raw_dir)
    prev_dir = np.r_[0.0, np.nan_to_num(last_raw_dir[:-1], nan=0.0)]
    bull = hh & (prev_dir <= 0)
    after_bull = np.where(bull, 1.0, prev_dir)
    bear = ll & (after_bull >= 0)

    # Exact scalar-like anchors reconstructed from events.
    direction = np.zeros(m)
    ah = np.full(m, np.nan)
    al = np.full(m, np.nan)
    ah_bar = np.full(m, np.nan)
    al_bar = np.full(m, np.nan)
    trend = 0
    cur_ah = cur_al = np.nan
    cur_ah_bar = cur_al_bar = np.nan
    for i in range(m):
        if bull[i]:
            trend = 1
            cur_al = last_l[i]
            # most recent low confirmation's pivot bar
            lows = np.flatnonzero(pl[: i + 1])
            cur_al_bar = (lows[-1] - n) if len(lows) else np.nan
            cur_ah = cand_h[i]
            cur_ah_bar = i - n
        if bear[i]:
            trend = -1
            cur_ah = last_h[i]
            highs = np.flatnonzero(ph[: i + 1])
            cur_ah_bar = (highs[-1] - n) if len(highs) else np.nan
            cur_al = cand_l[i]
            cur_al_bar = i - n
        if trend == 1 and not bull[i] and ph[i] and not np.isnan(cur_ah) and cand_h[i] > cur_ah:
            cur_ah = cand_h[i]
            cur_ah_bar = i - n
        if trend == -1 and not bear[i] and pl[i] and not np.isnan(cur_al) and cand_l[i] < cur_al:
            cur_al = cand_l[i]
            cur_al_bar = i - n
        direction[i] = trend
        ah[i], al[i] = cur_ah, cur_al
        ah_bar[i], al_bar[i] = cur_ah_bar, cur_al_bar
    return ph, pl, bull, bear, direction, ah, al, ah_bar, al_bar


def scalar_engine(high: np.ndarray, low: np.ndarray, n: int):
    m = len(high)
    window = n * 2 + 1
    last_h = last_l = prev_h = prev_l = np.nan
    last_h_bar = last_l_bar = np.nan
    trend = 0
    anchor_h = anchor_l = np.nan
    anchor_h_bar = anchor_l_bar = np.nan

    ph = np.zeros(m, bool)
    pl = np.zeros(m, bool)
    bull = np.zeros(m, bool)
    bear = np.zeros(m, bool)
    direction = np.zeros(m)
    ah = np.full(m, np.nan)
    al = np.full(m, np.nan)
    ah_bar = np.full(m, np.nan)
    al_bar = np.full(m, np.nan)

    for i in range(m):
        if i + 1 > window:
            idx = i - n
            p_hi = high[idx] if high[idx] == np.max(high[i - window + 1 : i + 1]) else np.nan
            p_lo = low[idx] if low[idx] == np.min(low[i - window + 1 : i + 1]) else np.nan
        else:
            p_hi = p_lo = np.nan
        ph[i] = not np.isnan(p_hi)
        pl[i] = not np.isnan(p_lo)

        if ph[i]:
            prev_h = last_h
            last_h = p_hi
            last_h_bar = i - n
        if pl[i]:
            prev_l = last_l
            last_l = p_lo
            last_l_bar = i - n

        b = bool(ph[i] and not np.isnan(prev_h) and p_hi > prev_h and trend <= 0)
        d = False
        if b:
            trend = 1
            anchor_l, anchor_l_bar = last_l, last_l_bar
            anchor_h, anchor_h_bar = p_hi, i - n
        if pl[i] and not np.isnan(prev_l) and p_lo < prev_l and trend >= 0:
            d = True
            trend = -1
            anchor_h, anchor_h_bar = last_h, last_h_bar
            anchor_l, anchor_l_bar = p_lo, i - n
        if trend == 1 and not b and ph[i] and not np.isnan(anchor_h) and p_hi > anchor_h:
            anchor_h, anchor_h_bar = p_hi, i - n
        if trend == -1 and not d and pl[i] and not np.isnan(anchor_l) and p_lo < anchor_l:
            anchor_l, anchor_l_bar = p_lo, i - n

        bull[i], bear[i] = b, d
        direction[i] = trend
        ah[i], al[i] = anchor_h, anchor_l
        ah_bar[i], al_bar[i] = anchor_h_bar, anchor_l_bar
    return ph, pl, bull, bear, direction, ah, al, ah_bar, al_bar


def same_float(a, b):
    return np.all((np.isnan(a) & np.isnan(b)) | np.isclose(a, b, rtol=0, atol=1e-12))


def main():
    for length in (3, 5, 10, 20, 50):
        for seed in range(100):
            rng = np.random.default_rng(100_000 + length * 1000 + seed)
            m = 1800
            close = 100 * np.exp(np.cumsum(rng.normal(0, 0.015, m)))
            spread = np.abs(rng.normal(0.008, 0.004, m))
            high = close * (1 + spread)
            low = close * (1 - spread)
            v = vector_engine(high, low, length)
            s = scalar_engine(high, low, length)
            names = ('pivot_high','pivot_low','bull_shift','bear_shift','direction','anchor_high','anchor_low','anchor_high_bar','anchor_low_bar')
            for name, got, exp in zip(names, v, s):
                ok = np.array_equal(got, exp) if got.dtype == bool else same_float(got, exp)
                if not ok:
                    idx = np.flatnonzero(~((np.isnan(got) & np.isnan(exp)) | np.isclose(got, exp, rtol=0, atol=1e-12))) if got.dtype != bool else np.flatnonzero(got != exp)
                    raise AssertionError(f'{name} mismatch length={length} seed={seed} first={idx[0] if len(idx) else None}')
    print('ChartPrime pivot/shift/anchor state: PASS (500 randomized histories)')


if __name__ == '__main__':
    main()
