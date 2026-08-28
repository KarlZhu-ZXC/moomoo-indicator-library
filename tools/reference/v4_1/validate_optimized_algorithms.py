from __future__ import annotations

import numpy as np
import pandas as pd


def bars_next(events):
    out = np.full(len(events), np.nan)
    nxt = None
    for i in range(len(events) - 1, -1, -1):
        if events[i]:
            nxt = i
        if nxt is not None:
            out[i] = nxt - i
    return out


def bars_last(events):
    out = np.full(len(events), np.nan)
    last = None
    for i, value in enumerate(events):
        if value:
            last = i
        if last is not None:
            out[i] = i - last
    return out


def bfill(values):
    return pd.Series(values).bfill().to_numpy()


def rolling_max(values, window):
    return pd.Series(values).rolling(window, min_periods=1).max().to_numpy()


def rolling_min(values, window):
    return pd.Series(values).rolling(window, min_periods=1).min().to_numpy()


def validate_current_extremes():
    for seed in range(500):
        rng = np.random.default_rng(seed)
        n = 1200
        source = np.cumsum(rng.normal(size=n)) + 100.0
        confirms = np.zeros(n, dtype=bool)
        indexes = sorted(rng.choice(np.arange(60, n - 10), size=30, replace=False))
        confirms[indexes] = True
        pivot_offset = int(rng.integers(3, 60))
        latest = indexes[-1]
        start = max(0, latest - pivot_offset, n - 501)
        age = np.arange(n - 1, -1, -1)
        start_age = (n - 1 - latest) + pivot_offset
        mask = age <= start_age
        got_high = rolling_max(np.where(mask, source, -1e9), 501)[-1]
        got_low = rolling_min(np.where(mask, source, 1e9), 501)[-1]
        if got_high != np.max(source[start:]) or got_low != np.min(source[start:]):
            raise AssertionError(f"current extreme mismatch seed={seed}")


def validate_confirmed_pivot_extremes():
    for seed in range(500):
        rng = np.random.default_rng(10_000 + seed)
        n = 1200
        values = np.cumsum(rng.normal(size=n)) + 100.0
        pivots = np.zeros(n, dtype=bool)
        pivot_indexes = sorted(rng.choice(np.arange(40, n), size=80, replace=False))
        pivots[pivot_indexes] = True
        shift = int(rng.integers(100, n - 1))
        valid_indexes = [idx for idx in pivot_indexes if idx >= shift and idx >= n - 501]
        if not valid_indexes:
            continue
        age = np.arange(n - 1, -1, -1)
        shift_age = n - 1 - shift
        mask = (age <= shift_age) & pivots
        got_high = rolling_max(np.where(mask, values, -1e9), 501)[-1]
        got_low = rolling_min(np.where(mask, values, 1e9), 501)[-1]
        expected = values[valid_indexes]
        if got_high != expected.max() or got_low != expected.min():
            raise AssertionError(f"pivot extreme mismatch seed={seed}")


def validate_ob_slot_selection(slot_count):
    for seed in range(300):
        rng = np.random.default_rng(20_000 + seed)
        n = 2200
        high = np.cumsum(rng.normal(size=n)) + 150.0 + rng.random(n)
        low = high - rng.random(n) * 4.0
        close = (high + low) / 2.0
        events = np.zeros(n, dtype=bool)
        spans = np.full(n, np.nan)
        biases = np.full(n, np.nan)
        references = []
        index = 60
        count = 0
        while index < n:
            span = int(rng.integers(2, min(180, index) + 1))
            bias = 1.0 if rng.random() < 0.5 else -1.0
            events[index] = True
            spans[index] = span
            biases[index] = bias
            start = index - span
            candidate = low[start:index] if bias > 0 else high[start:index]
            target = candidate.min() if bias > 0 else candidate.max()
            # Pine array.indexof() selects the oldest equal extreme.
            selected = start + int(np.where(candidate == target)[0][0])
            references.append((index, selected, count % slot_count))
            count += 1
            index += int(rng.integers(5, 35))

        event_count = np.cumsum(events.astype(float))
        for slot_index in range(slot_count):
            slot_event = events & (((event_count - 1.0) % slot_count) == slot_index)
            next_event = bars_next(slot_event)
            span = bfill(np.where(slot_event, spans, np.nan))
            bias = bfill(np.where(slot_event, biases, np.nan))
            generation = (event_count - 1.0 - ((event_count - 1.0) % slot_count)) / slot_count
            generation = bfill(np.where(slot_event, generation, np.nan))
            scale = bfill(np.where(slot_event, np.maximum(np.abs(close), 1.0), np.nan))
            interval = (~np.isnan(next_event)) & (~np.isnan(span)) & (next_event >= 1) & (next_event <= span) & (next_event <= 500)
            select_value = np.where(bias > 0, -low / scale, high / scale)
            score = generation * 1000.0 + select_value + np.nan_to_num(next_event) * 1e-9
            masked = np.where(interval, score, -1e12)
            rolling = rolling_max(masked, 501)
            best = bfill(np.where(slot_event, rolling, np.nan))
            selected_bar = interval & np.isclose(score, best, rtol=0.0, atol=1e-12)
            selected_age = bars_last(selected_bar)
            for event_index, expected_index, expected_slot in references:
                if expected_slot != slot_index:
                    continue
                if spans[event_index] > 500:
                    expected_start = event_index - 500
                    candidate = low[expected_start:event_index] if biases[event_index] > 0 else high[expected_start:event_index]
                    target = candidate.min() if biases[event_index] > 0 else candidate.max()
                    expected_index = expected_start + int(np.where(candidate == target)[0][0])
                got_index = event_index - int(selected_age[event_index])
                if got_index != expected_index:
                    raise AssertionError(
                        f"OB selection mismatch slots={slot_count} seed={seed} event={event_index} expected={expected_index} got={got_index}"
                    )


def validate_ranking():
    rng = np.random.default_rng(30_000)
    for slots in (8, 10, 16):
        for _ in range(500):
            active = rng.random(slots) > 0.35
            ages = rng.choice(np.arange(1, 5000), size=slots, replace=False)
            ranks = np.zeros(slots, dtype=int)
            for i in range(slots):
                ranks[i] = sum(bool(active[j] and ages[j] < ages[i]) for j in range(slots) if j != i)
            expected = [idx for idx in np.argsort(ages) if active[idx]]
            got = [idx for idx in np.argsort(ranks) if active[idx]]
            if expected != got:
                raise AssertionError("active rank mismatch")


if __name__ == "__main__":
    validate_current_extremes()
    validate_confirmed_pivot_extremes()
    validate_ob_slot_selection(32)
    validate_ranking()
    print("current trailing extremes: PASS (500 cases)")
    print("OTE confirmed-pivot extremes: PASS (500 cases)")
    print("OB interval selection: PASS (300 randomized histories, 32 lanes)")
    print("active-slot ranking: PASS (1500 cases)")
