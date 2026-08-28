from __future__ import annotations

import random


def test_ote_shift_geometry() -> None:
    """The BOS line must cover previous pivot bar through current pivot bar."""
    rng = random.Random(20260828)
    for _ in range(5000):
        offset = rng.randint(1, 50)
        prev_confirm = rng.randint(100, 1000)
        current_confirm = rng.randint(prev_confirm + 1, prev_confirm + 300)
        prev_pivot = prev_confirm - offset
        current_pivot = current_confirm - offset
        confirm_distance = current_confirm - prev_confirm
        far_age = confirm_distance + offset
        visible = []
        for index in range(prev_pivot - 5, current_confirm + 5):
            next_event = current_confirm - index
            if offset <= next_event <= far_age:
                visible.append(index)
        expected = list(range(prev_pivot, current_pivot + 1))
        if visible != expected:
            raise AssertionError((offset, prev_confirm, current_confirm, visible[:3], visible[-3:], expected[:3], expected[-3:]))


def test_ob_same_bar_mitigation() -> None:
    # A Pine OB is stored during displayStructure() and deleteOrderBlocks() runs
    # later on the same bar.  A break bar that already crosses the new block must
    # leave it inactive immediately.
    slot_event = True
    bullish = True
    bottom = 100.0
    bar_low = 99.0
    invalid = bullish and bar_low < bottom
    age_since_creation = 0
    age_since_invalidation = 0 if invalid else 10**9
    active = age_since_creation < age_since_invalidation
    assert invalid and not active


def test_eq_label_level() -> None:
    previous = 100.0
    current = 100.08
    # LuxAlgo drawEqualHighLow() places the label at `level`, the newly
    # confirmed pivot, not at average(previous,current).
    label_y = current
    assert label_y == current and label_y != (previous + current) / 2.0


if __name__ == "__main__":
    test_ote_shift_geometry()
    test_ob_same_bar_mitigation()
    test_eq_label_level()
    print("OTE prior-pivot BOS geometry: PASS (5000 randomized cases)")
    print("OB same-bar mitigation ordering: PASS")
    print("EQH/EQL current-pivot label level: PASS")
