# Smart Money Concepts [LuxAlgo] source-aligned port — FVG / Zones module v3.2
# Target: moomoo Python custom indicator
# Source baseline: LuxAlgo open Pine v5 mirror, commit 31756c8615aff4cefe9cf97350e78bd427f663cd
# License: CC BY-NC-SA 4.0; original © LuxAlgo.
#
# Exact within current chart timeframe:
# - source FVG condition, auto threshold, split boxes, mitigation
# - current active gaps selected chronologically across both biases
# - Premium/Equilibrium/Discount percentages and trailing-extreme range
# Platform boundary: arbitrary request.security() timeframe and D/W/M levels are
# not exposed by the client-confirmed moomoo Python indicator runtime.

import math
from ftool import *

indicator(
    "SMC_IMB",
    "SMC Imbalance",
    True,
    "Source-aligned current-timeframe FVGs and Premium/Equilibrium/Discount zones.",
)

monochrome = input_parameter("Style: Monochrome", False)
show_fvg = input_parameter("Fair Value Gaps", False)
fvg_auto_threshold = input_parameter("Auto Threshold", True)
fvg_extend = input_parameter("Extend FVG", 1)
fvg_render_cap = input_parameter("FVG Render Cap 1-20", 20)
show_fvg_labels = input_parameter("Show FVG Labels", True)
fvg_label_count = input_parameter("FVG Label Count 0-20", 20)
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
_INTERNAL_UNUSED = 5
_PHYSICAL_SLOTS = 48
_VISIBLE_SLOTS = 20
_TRAIL_SCAN = 500
_false = c != c
_nan = c * math.nan
is_last = curr_bars_count(c) == 0
x_age = curr_bars_count(c)


def _age(cond):
    return replace_na(bars_last(cond), _BIG)


def _broadcast_last(x):
    return fill_na(iff(is_last, x, math.nan), "backward")


def _swing_state(length):
    high_candidate = ref(h, length) > h.hhv(length)
    low_candidate = (ref(l, length) < l.llv(length)) & (~high_candidate)
    prev_high_age = replace_na(ref(bars_last(high_candidate), 1), _BIG)
    prev_low_age = replace_na(ref(bars_last(low_candidate), 1), _BIG)
    previous_leg_is_bearish = prev_high_age <= prev_low_age
    top_confirm = high_candidate & (~previous_leg_is_bearish)
    bottom_confirm = low_candidate & previous_leg_is_bearish
    return top_confirm, bottom_confirm


def _scan_extreme_since(confirm_event, pivot_offset, source, find_maximum):
    start_age = _age(confirm_event) + pivot_offset
    has_start = _age(confirm_event) < _BIG
    best = _nan
    best_offset = _nan
    for k in range(0, _TRAIL_SCAN + 1):
        candidate = ref(source, k)
        eligible = has_start & (start_age >= k)
        if find_maximum:
            better = eligible & (is_na(best) | (candidate > best))
        else:
            better = eligible & (is_na(best) | (candidate < best))
        best = iff(better, candidate, best)
        best_offset = iff(better, k, best_offset)
    return best, best_offset, start_age


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


def _recent_active(slots, visible_count):
    remaining = []
    for zone in slots:
        remaining.append(iff(zone[3], zone[4], _BIG))
    selected = []
    for _rank in range(visible_count):
        best_age = remaining[0]
        for candidate in remaining[1:]:
            best_age = min(best_age, candidate)
        has_zone = best_age < _BIG
        top = _nan
        bottom = _nan
        bias = _nan
        for idx in range(len(slots)):
            match = has_zone & (remaining[idx] == best_age)
            top = iff(match, slots[idx][0], top)
            bottom = iff(match, slots[idx][1], bottom)
            bias = iff(match, slots[idx][2], bias)
        selected.append((top, bottom, bias, has_zone, best_age))
        next_remaining = []
        for age_value in remaining:
            next_remaining.append(iff(age_value == best_age, _BIG, age_value))
        remaining = next_remaining
    return selected


def _freeze_current_fvg(zone, extend_bars):
    top = fill_na(iff(is_last & zone[3], zone[0], math.nan), "backward")
    bottom = fill_na(iff(is_last & zone[3], zone[1], math.nan), "backward")
    bias = fill_na(iff(is_last & zone[3], zone[2], math.nan), "backward")
    event_age = fill_na(iff(is_last & zone[3], zone[4], math.nan), "backward")
    left_age = event_age + 1.0
    right_age = max(event_age - extend_bars, 0.0)
    exists = (~is_na(top)) & (~is_na(bottom)) & (~is_na(event_age))
    visible = exists & (x_age <= left_age) & (x_age >= right_age)
    midpoint_sum = left_age + right_age
    label_here = visible & (x_age * 2.0 <= midpoint_sum) & (x_age * 2.0 > midpoint_sum - 2.0)
    label_y = (top + bottom) / 2.0
    return top, bottom, bias, visible, label_here, label_y


def _or_breaks(slots):
    result = _false
    for zone in slots:
        result = result | zone[5]
    return result


# Source FVG formula for current chart timeframe (newTimeframe is true each bar).
# Source defaults FVG off, so avoid constructing 48 object states until enabled.
if show_fvg:
    bar_index_like = max(bars_count(c) - 1.0, 1.0)
    bar_delta = replace_na((ref(c, 1) - ref(o, 1)) / (ref(o, 1) * 100.0), 0.0)
    threshold_auto = abs(bar_delta).sum(0) / bar_index_like * 2.0
    threshold = threshold_auto if fvg_auto_threshold else c * 0.0
    bull_event = (l > ref(h, 2)) & (ref(c, 1) > ref(h, 2)) & (bar_delta > threshold)
    bear_event = (h < ref(l, 2)) & (ref(c, 1) < ref(l, 2)) & ((0.0 - bar_delta) > threshold)
    slots = _build_fvg_slots(bull_event, bear_event, l, ref(h, 2), h, ref(l, 2), _PHYSICAL_SLOTS)
    selected = [_freeze_current_fvg(zone, fvg_extend) for zone in _recent_active(slots, _VISIBLE_SLOTS)]
else:
    bull_event = _false
    bear_event = _false
    slots = []
    selected = []
    for _slot in range(_VISIBLE_SLOTS):
        selected.append((_nan, _nan, _nan, _false, _false, _nan))

visible = []
colors = []
label_visible = []
label_colors = []
for idx in range(_VISIBLE_SLOTS):
    enabled = show_fvg and (fvg_render_cap >= idx + 1)
    label_enabled = enabled and show_fvg_labels and (fvg_label_count >= idx + 1)
    visible.append(selected[idx][3] if enabled else _false)
    colors.append(iff(selected[idx][2] > 0, bull_fvg_fill, bear_fvg_fill))
    label_visible.append(selected[idx][4] if label_enabled else _false)
    label_colors.append(iff(selected[idx][2] > 0, bull, bear))

# Source-aligned trailing range shared by Strong/Weak and zones.
if show_zones:
    top_confirm, bottom_confirm = _swing_state(swing_length)
    top_raw, top_offset_raw, top_start_age = _scan_extreme_since(top_confirm, swing_length, h, True)
    bottom_raw, bottom_offset_raw, bottom_start_age = _scan_extreme_since(bottom_confirm, swing_length, l, False)
    zone_high = _broadcast_last(top_raw)
    zone_low = _broadcast_last(bottom_raw)
    latest_pivot_age = _broadcast_last(min(top_start_age, bottom_start_age))
    zone_exists = (~is_na(zone_high)) & (~is_na(zone_low)) & (~is_na(latest_pivot_age))
    zone_visible = zone_exists & (x_age <= latest_pivot_age)
else:
    zone_high = _nan
    zone_low = _nan
    latest_pivot_age = _nan
    zone_exists = _false
    zone_visible = _false
zone_range = zone_high - zone_low
premium_bottom = 0.95 * zone_high + 0.05 * zone_low
eq_top = 0.525 * zone_high + 0.475 * zone_low
eq_bottom = 0.525 * zone_low + 0.475 * zone_high
discount_top = 0.95 * zone_low + 0.05 * zone_high
zone_mid = (zone_high + zone_low) / 2.0
zone_midpoint = zone_visible & (x_age * 2 >= latest_pivot_age) & (x_age * 2 < latest_pivot_age + 2)
zone_last = is_last & zone_exists if show_zones else _false
zone_gap = max((zone_high - zone_low) * 0.01, c * 0.001)

# GLOBAL PLOTS — 46/50
plot_fillcolor("FVG 1", selected[0][0], selected[0][1], visible[0], colors[0], 0)
plot_fillcolor("FVG 2", selected[1][0], selected[1][1], visible[1], colors[1], 0)
plot_fillcolor("FVG 3", selected[2][0], selected[2][1], visible[2], colors[2], 0)
plot_fillcolor("FVG 4", selected[3][0], selected[3][1], visible[3], colors[3], 0)
plot_fillcolor("FVG 5", selected[4][0], selected[4][1], visible[4], colors[4], 0)
plot_fillcolor("FVG 6", selected[5][0], selected[5][1], visible[5], colors[5], 0)
plot_fillcolor("FVG 7", selected[6][0], selected[6][1], visible[6], colors[6], 0)
plot_fillcolor("FVG 8", selected[7][0], selected[7][1], visible[7], colors[7], 0)
plot_fillcolor("FVG 9", selected[8][0], selected[8][1], visible[8], colors[8], 0)
plot_fillcolor("FVG 10", selected[9][0], selected[9][1], visible[9], colors[9], 0)
plot_fillcolor("FVG 11", selected[10][0], selected[10][1], visible[10], colors[10], 0)
plot_fillcolor("FVG 12", selected[11][0], selected[11][1], visible[11], colors[11], 0)
plot_fillcolor("FVG 13", selected[12][0], selected[12][1], visible[12], colors[12], 0)
plot_fillcolor("FVG 14", selected[13][0], selected[13][1], visible[13], colors[13], 0)
plot_fillcolor("FVG 15", selected[14][0], selected[14][1], visible[14], colors[14], 0)
plot_fillcolor("FVG 16", selected[15][0], selected[15][1], visible[15], colors[15], 0)
plot_fillcolor("FVG 17", selected[16][0], selected[16][1], visible[16], colors[16], 0)
plot_fillcolor("FVG 18", selected[17][0], selected[17][1], visible[17], colors[17], 0)
plot_fillcolor("FVG 19", selected[18][0], selected[18][1], visible[18], colors[18], 0)
plot_fillcolor("FVG 20", selected[19][0], selected[19][1], visible[19], colors[19], 0)
plot_text("FVG tag 1", label_visible[0], selected[0][5], "FVG", label_colors[0], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 2", label_visible[1], selected[1][5], "FVG", label_colors[1], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 3", label_visible[2], selected[2][5], "FVG", label_colors[2], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 4", label_visible[3], selected[3][5], "FVG", label_colors[3], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 5", label_visible[4], selected[4][5], "FVG", label_colors[4], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 6", label_visible[5], selected[5][5], "FVG", label_colors[5], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 7", label_visible[6], selected[6][5], "FVG", label_colors[6], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 8", label_visible[7], selected[7][5], "FVG", label_colors[7], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 9", label_visible[8], selected[8][5], "FVG", label_colors[8], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 10", label_visible[9], selected[9][5], "FVG", label_colors[9], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 11", label_visible[10], selected[10][5], "FVG", label_colors[10], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 12", label_visible[11], selected[11][5], "FVG", label_colors[11], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 13", label_visible[12], selected[12][5], "FVG", label_colors[12], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 14", label_visible[13], selected[13][5], "FVG", label_colors[13], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 15", label_visible[14], selected[14][5], "FVG", label_colors[14], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 16", label_visible[15], selected[15][5], "FVG", label_colors[15], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 17", label_visible[16], selected[16][5], "FVG", label_colors[16], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 18", label_visible[17], selected[17][5], "FVG", label_colors[17], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 19", label_visible[18], selected[18][5], "FVG", label_colors[18], fvg_label_size, 0, 0, 0)
plot_text("FVG tag 20", label_visible[19], selected[19][5], "FVG", label_colors[19], fvg_label_size, 0, 0, 0)
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
