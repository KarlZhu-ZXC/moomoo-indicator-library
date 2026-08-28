# Smart Money Concepts [LuxAlgo] — FVG / Zones module v4.1 fidelity baseline
# Target: moomoo Python custom indicator
# Source baseline: LuxAlgo open Pine v5 mirror, commit 31756c8615aff4cefe9cf97350e78bd427f663cd
# License: CC BY-NC-SA 4.0; original © LuxAlgo.
#
# Optimization strategy:
# - 20 bounded rotating FVG states instead of 48 states plus 20 selection passes
# - in-place age ranking for current active FVGs
# - one native HHV and one LLV for the current trailing zone; no 500-layer scan

import math
from ftool import *

indicator(
    "SMC_IMB",
    "SMC Imbalance",
    True,
    "Memory-optimized current-timeframe FVGs and source-aligned Premium/Equilibrium/Discount zones.",
)

monochrome = input_parameter("Style: Monochrome", False)
show_fvg = input_parameter("Fair Value Gaps", False)
fvg_auto_threshold = input_parameter("Auto Threshold", True)
fvg_extend = input_parameter("Extend FVG", 1)
fvg_render_cap = input_parameter("FVG Render Cap 1-20", 20)
show_fvg_labels = input_parameter("Show FVG Labels", True)
fvg_label_count = input_parameter("FVG Label Count 0-5", 5)
fvg_label_size = input_parameter("FVG Label Size 1-3", 1)
show_zones = input_parameter("Premium/Discount Zones", False)
swing_length = input_parameter("Swing Length", 50)

if monochrome:
    bull = Color.hex("#B2B5BE")
    bear = Color.hex("#5D606B")
    bull_fvg_fill = Color.rgb(178, 181, 190, 76)
    bear_fvg_fill = Color.rgb(93, 96, 107, 76)
    premium_fill = Color.rgb(93, 96, 107, 52)
    equilibrium_fill = Color.rgb(178, 181, 190, 52)
    discount_fill = Color.rgb(178, 181, 190, 52)
else:
    bull = Color.hex("#089981")
    bear = Color.hex("#F23645")
    bull_fvg_fill = Color.rgb(0, 255, 104, 76)
    bear_fvg_fill = Color.rgb(255, 0, 8, 76)
    premium_fill = Color.rgb(242, 54, 69, 52)
    equilibrium_fill = Color.rgb(135, 139, 148, 52)
    discount_fill = Color.rgb(8, 153, 129, 52)
neutral = Color.hex("#878B94")

o = open()
h = high()
l = low()
c = close()
_BIG = 1000000000.0
_FVG_SLOTS = 20
_RANGE_MAX = 500
_false = c != c
_nan = c * math.nan
is_last = curr_bars_count(c) == 0
x_age = curr_bars_count(c)


def _age(cond):
    return replace_na(bars_last(cond), _BIG)


def _broadcast_last(x):
    return fill_na(iff(is_last, x, math.nan), "backward")


def _broadcast_last_bool(cond):
    return _broadcast_last(iff(cond, 1.0, 0.0)) > 0.5


def _swing_state(length):
    high_candidate = ref(h, length) > h.hhv(length)
    low_candidate = (ref(l, length) < l.llv(length)) & (~high_candidate)
    prev_high_age = replace_na(ref(bars_last(high_candidate), 1), _BIG)
    prev_low_age = replace_na(ref(bars_last(low_candidate), 1), _BIG)
    previous_leg_is_bearish = prev_high_age <= prev_low_age
    top_confirm = high_candidate & (~previous_leg_is_bearish)
    bottom_confirm = low_candidate & previous_leg_is_bearish
    return top_confirm, bottom_confirm


def _current_extreme_since(confirm_event, pivot_offset, source, find_maximum):
    start_age = _broadcast_last(_age(confirm_event) + pivot_offset)
    has_start = start_age < _BIG
    in_range = has_start & (x_age <= start_age)
    if find_maximum:
        masked = iff(in_range, source, 0.0 - _BIG)
        extreme = _broadcast_last(masked.hhv(_RANGE_MAX + 1))
    else:
        masked = iff(in_range, source, _BIG)
        extreme = _broadcast_last(masked.llv(_RANGE_MAX + 1))
    valid = has_start & (~is_na(extreme)) & (abs(extreme) < _BIG * 0.5)
    return iff(valid, extreme, math.nan), start_age


def _build_fvg_slots(bull_event, bear_event, bull_top, bull_bottom, bear_top, bear_bottom, physical_slots):
    event = bull_event | bear_event
    event_count = iff(event, 1.0, 0.0).sum(0)
    slots = []
    for slot_index in range(physical_slots):
        slot_event = event & (((event_count - 1.0) % physical_slots) == slot_index)
        top = value_when(slot_event, iff(bull_event, bull_top, bear_top))
        bottom = value_when(slot_event, iff(bull_event, bull_bottom, bear_bottom))
        bias = value_when(slot_event, iff(bull_event, 1.0, -1.0))
        invalid = ((bias > 0) & (l < bottom)) | ((bias < 0) & (h > top))
        invalid_after_creation = invalid & (~slot_event)
        age = _age(slot_event)
        active = (age < _age(invalid_after_creation)) & (~is_na(top)) & (~is_na(bottom))
        break_event = invalid_after_creation & ref(active, 1)
        slots.append((top, bottom, bias, active, age, break_event))
    return slots


def _rank_active(slots):
    ranks = []
    for index in range(len(slots)):
        rank = c * 0.0
        for other in range(len(slots)):
            if other != index:
                rank = rank + iff(slots[other][3] & (slots[other][4] < slots[index][4]), 1.0, 0.0)
        ranks.append(rank)
    return ranks


def _freeze_fvg_slot(slot, rank, visible_count, extend_bars):
    visible_now = slot[3] & (rank < visible_count)
    current_visible = _broadcast_last_bool(visible_now)
    top = _broadcast_last(slot[0])
    bottom = _broadcast_last(slot[1])
    bias = _broadcast_last(slot[2])
    event_age = _broadcast_last(slot[4])
    left_age = event_age + 1.0
    right_age = max(event_age - extend_bars, 0.0)
    valid = current_visible & (~is_na(top)) & (~is_na(bottom)) & (~is_na(event_age))
    visible = valid & (x_age <= left_age) & (x_age >= right_age)
    return top, bottom, bias, visible, event_age, left_age, right_age


def _select_rank(slots, ranks, target_rank):
    top = _nan
    bottom = _nan
    bias = _nan
    age = _nan
    exists = _false
    for index in range(len(slots)):
        match = slots[index][3] & (ranks[index] == target_rank)
        top = iff(match, slots[index][0], top)
        bottom = iff(match, slots[index][1], bottom)
        bias = iff(match, slots[index][2], bias)
        age = iff(match, slots[index][4], age)
        exists = exists | match
    return _broadcast_last(top), _broadcast_last(bottom), _broadcast_last(bias), _broadcast_last(age), _broadcast_last_bool(exists)


def _or_breaks(slots):
    result = _false
    for slot in slots:
        result = result | slot[5]
    return result


# Source FVG formula for the current chart timeframe.
if show_fvg:
    bar_index_like = max(bars_count(c) - 1.0, 1.0)
    bar_delta = replace_na((ref(c, 1) - ref(o, 1)) / (ref(o, 1) * 100.0), 0.0)
    threshold_auto = abs(bar_delta).sum(0) / bar_index_like * 2.0
    threshold = threshold_auto if fvg_auto_threshold else c * 0.0
    bull_event = (l > ref(h, 2)) & (ref(c, 1) > ref(h, 2)) & (bar_delta > threshold)
    bear_event = (h < ref(l, 2)) & (ref(c, 1) < ref(l, 2)) & ((0.0 - bar_delta) > threshold)
    slots = _build_fvg_slots(bull_event, bear_event, l, ref(h, 2), h, ref(l, 2), _FVG_SLOTS)
    ranks = _rank_active(slots)
    frozen = [_freeze_fvg_slot(slots[index], ranks[index], fvg_render_cap, fvg_extend) for index in range(_FVG_SLOTS)]
else:
    bull_event = _false
    bear_event = _false
    slots = []
    ranks = []
    frozen = [(_nan, _nan, _nan, _false, _nan, _nan, _nan) for _ in range(_FVG_SLOTS)]

fvg_colors = [iff(zone[2] > 0, bull_fvg_fill, bear_fvg_fill) for zone in frozen]

# Optional labels for the five most recent active FVGs.
fvg_labels = []
for target in range(5):
    if show_fvg:
        zone = _select_rank(slots, ranks, target)
    else:
        zone = (_nan, _nan, _nan, _nan, _false)
    enabled = show_fvg_labels and (fvg_label_count >= target + 1)
    event_age = zone[3]
    left_age = event_age + 1.0
    right_age = max(event_age - fvg_extend, 0.0)
    midpoint = left_age + right_age
    label_here = zone[4] & (x_age * 2.0 <= midpoint) & (x_age * 2.0 > midpoint - 2.0)
    cond = label_here if enabled else _false
    y = (zone[0] + zone[1]) / 2.0
    color = iff(zone[2] > 0, bull, bear)
    fvg_labels.append((cond, y, color))

# Source-aligned current trailing range for Premium/Discount zones.
if show_zones:
    top_confirm, bottom_confirm = _swing_state(swing_length)
    zone_high, top_start_age = _current_extreme_since(top_confirm, swing_length, h, True)
    zone_low, bottom_start_age = _current_extreme_since(bottom_confirm, swing_length, l, False)
    latest_pivot_age = min(top_start_age, bottom_start_age)
    zone_exists = (~is_na(zone_high)) & (~is_na(zone_low)) & (zone_high > zone_low) & (latest_pivot_age < _BIG)
    zone_visible = zone_exists & (x_age <= latest_pivot_age)
else:
    zone_high = _nan
    zone_low = _nan
    latest_pivot_age = _nan
    zone_exists = _false
    zone_visible = _false

premium_bottom = 0.95 * zone_high + 0.05 * zone_low
eq_top = 0.525 * zone_high + 0.475 * zone_low
eq_bottom = 0.525 * zone_low + 0.475 * zone_high
discount_top = 0.95 * zone_low + 0.05 * zone_high
zone_mid = (zone_high + zone_low) / 2.0
zone_midpoint = zone_visible & (x_age * 2.0 >= latest_pivot_age) & (x_age * 2.0 < latest_pivot_age + 2.0)
zone_last = is_last & zone_exists if show_zones else _false
zone_gap = max((zone_high - zone_low) * 0.01, c * 0.001)

# GLOBAL PLOTS — 31/50
plot_fillcolor("FVG 1", frozen[0][0], frozen[0][1], frozen[0][3], fvg_colors[0], 0)
plot_fillcolor("FVG 2", frozen[1][0], frozen[1][1], frozen[1][3], fvg_colors[1], 0)
plot_fillcolor("FVG 3", frozen[2][0], frozen[2][1], frozen[2][3], fvg_colors[2], 0)
plot_fillcolor("FVG 4", frozen[3][0], frozen[3][1], frozen[3][3], fvg_colors[3], 0)
plot_fillcolor("FVG 5", frozen[4][0], frozen[4][1], frozen[4][3], fvg_colors[4], 0)
plot_fillcolor("FVG 6", frozen[5][0], frozen[5][1], frozen[5][3], fvg_colors[5], 0)
plot_fillcolor("FVG 7", frozen[6][0], frozen[6][1], frozen[6][3], fvg_colors[6], 0)
plot_fillcolor("FVG 8", frozen[7][0], frozen[7][1], frozen[7][3], fvg_colors[7], 0)
plot_fillcolor("FVG 9", frozen[8][0], frozen[8][1], frozen[8][3], fvg_colors[8], 0)
plot_fillcolor("FVG 10", frozen[9][0], frozen[9][1], frozen[9][3], fvg_colors[9], 0)
plot_fillcolor("FVG 11", frozen[10][0], frozen[10][1], frozen[10][3], fvg_colors[10], 0)
plot_fillcolor("FVG 12", frozen[11][0], frozen[11][1], frozen[11][3], fvg_colors[11], 0)
plot_fillcolor("FVG 13", frozen[12][0], frozen[12][1], frozen[12][3], fvg_colors[12], 0)
plot_fillcolor("FVG 14", frozen[13][0], frozen[13][1], frozen[13][3], fvg_colors[13], 0)
plot_fillcolor("FVG 15", frozen[14][0], frozen[14][1], frozen[14][3], fvg_colors[14], 0)
plot_fillcolor("FVG 16", frozen[15][0], frozen[15][1], frozen[15][3], fvg_colors[15], 0)
plot_fillcolor("FVG 17", frozen[16][0], frozen[16][1], frozen[16][3], fvg_colors[16], 0)
plot_fillcolor("FVG 18", frozen[17][0], frozen[17][1], frozen[17][3], fvg_colors[17], 0)
plot_fillcolor("FVG 19", frozen[18][0], frozen[18][1], frozen[18][3], fvg_colors[18], 0)
plot_fillcolor("FVG 20", frozen[19][0], frozen[19][1], frozen[19][3], fvg_colors[19], 0)
plot_text("FVG tag 1", fvg_labels[0][0], fvg_labels[0][1], "FVG", fvg_labels[0][2], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 2", fvg_labels[1][0], fvg_labels[1][1], "FVG", fvg_labels[1][2], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 3", fvg_labels[2][0], fvg_labels[2][1], "FVG", fvg_labels[2][2], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 4", fvg_labels[3][0], fvg_labels[3][1], "FVG", fvg_labels[3][2], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 5", fvg_labels[4][0], fvg_labels[4][1], "FVG", fvg_labels[4][2], fvg_label_size, 0, 0, 0)
plot_fillcolor("Premium", zone_high, premium_bottom, zone_visible, premium_fill, 0)
plot_fillcolor("Equilibrium", eq_top, eq_bottom, zone_visible, equilibrium_fill, 0)
plot_fillcolor("Discount", discount_top, zone_low, zone_visible, discount_fill, 0)
plot_text("Premium label", zone_midpoint, zone_high + zone_gap, "Premium", bear, 2, 0, 0, 0)
plot_text("Equilibrium label", zone_last, zone_mid, "Equilibrium", neutral, 2, 0, 0, 0)
plot_text("Discount label", zone_midpoint, zone_low - zone_gap, "Discount", bull, 2, 0, 0, 0)

output_parameter(
    bullish_fvg_created=bull_event,
    bearish_fvg_created=bear_event,
    fvg_filled=_or_breaks(slots),
)
