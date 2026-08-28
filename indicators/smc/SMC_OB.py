# Smart Money Concepts [LuxAlgo] — Order Blocks module v4.1 fidelity baseline
# Target: moomoo Python custom indicator
# Source baseline: LuxAlgo open Pine v5 mirror, commit 31756c8615aff4cefe9cf97350e78bd427f663cd
# License: CC BY-NC-SA 4.0; original © LuxAlgo.
#
# Optimization strategy:
# - no 500-iteration ref()/iff() scan
# - 32 interleaved native-HHV candidate lanes preserve overlapping pivot->break
#   intervals without building a hundreds-deep Sequence chain
# - 20 bounded current-object slots per family retain Pine's 1..20 setting
# - current active blocks are ranked in-place instead of copied through 20
#   repeated selection passes

import math
from ftool import *

indicator(
    "SMC_OB",
    "SMC Order Blocks",
    True,
    "Memory-optimized current active Internal/Swing order blocks with source-aligned selection, volatility parsing and mitigation.",
)

monochrome = input_parameter("Style: Monochrome", False)
show_internal_ob = input_parameter("Internal Order Blocks", True)
internal_ob_count = input_parameter("Internal OB Count 1-20", 5)
show_swing_ob = input_parameter("Swing Order Blocks", False)
swing_ob_count = input_parameter("Swing OB Count 1-20", 5)
filter_mode = input_parameter("OB Filter 0ATR 1CumRange", 0)
mitigation_mode = input_parameter("Mitigation 0HighLow1Close", 0)
internal_confluence = input_parameter("Confluence Filter", False)
swing_length = input_parameter("Swing Length", 50)
show_ob_labels = input_parameter("Show OB Labels", True)
ob_label_count = input_parameter("OB Label Count 0-3", 3)
ob_label_size = input_parameter("OB Label Size 1-3", 1)

if monochrome:
    internal_bull_fill = Color.rgb(178, 181, 190, 52)
    internal_bear_fill = Color.rgb(93, 96, 107, 52)
    swing_bull_fill = Color.rgb(178, 181, 190, 52)
    swing_bear_fill = Color.rgb(93, 96, 107, 52)
    internal_bull_text = Color.hex("#B2B5BE")
    internal_bear_text = Color.hex("#5D606B")
    swing_bull_text = Color.hex("#B2B5BE")
    swing_bear_text = Color.hex("#5D606B")
else:
    internal_bull_fill = Color.rgb(49, 121, 245, 52)
    internal_bear_fill = Color.rgb(247, 124, 128, 52)
    swing_bull_fill = Color.rgb(24, 72, 204, 52)
    swing_bear_fill = Color.rgb(178, 40, 51, 52)
    internal_bull_text = Color.hex("#3179F5")
    internal_bear_text = Color.hex("#F77C80")
    swing_bull_text = Color.hex("#1848CC")
    swing_bear_text = Color.hex("#B22833")

o = open()
h = high()
l = low()
c = close()
_BIG = 1000000000.0
_SCORE_STEP = 1000.0
_INTERNAL_LEN = 5
_OB_SCAN = 500
_CANDIDATE_LANES = 32
_STATE_SLOTS = 20
_false = c != c
_true = c == c
_nan = c * math.nan
is_last = curr_bars_count(c) == 0
x_age = curr_bars_count(c)


def _age(cond):
    return replace_na(bars_last(cond), _BIG)


def _previous_age(cond):
    return replace_na(ref(bars_last(cond), 1), _BIG)


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
    top_level = value_when(top_confirm, ref(h, length))
    bottom_level = value_when(bottom_confirm, ref(l, length))
    return top_confirm, bottom_confirm, top_level, bottom_level


def _crossover(x, y):
    return (x > y) & (ref(x, 1) <= ref(y, 1))


def _crossunder(x, y):
    return (x < y) & (ref(x, 1) >= ref(y, 1))


def _once_after_pivot(raw_break, pivot_confirm):
    return raw_break & (_age(pivot_confirm) <= _previous_age(raw_break))


def _select_ob_events(bull_event, bear_event, bull_pivot, bear_pivot, pivot_offset, parsed_high, parsed_low, candidate_lanes):
    """Source-aligned pivot->break extreme selection with bounded native nodes.

    Events are interleaved across 32 lanes so overlapping intervals do not
    overwrite one another.  Each lane builds a future-aware pivot..break-1 mask
    and uses one native HHV on a generation-weighted score.  Bullish events
    maximize -parsedLow; bearish events maximize parsedHigh.  A tiny age term
    reproduces Pine array.indexof()'s oldest-equal choice.
    """
    event = bull_event | bear_event
    event_count = iff(event, 1.0, 0.0).sum(0)
    generation = (event_count - 1.0 - ((event_count - 1.0) % candidate_lanes)) / candidate_lanes
    event_bias = iff(bear_event, -1.0, 1.0)
    span_at_event = iff(bull_event, _age(bull_pivot) + pivot_offset, _age(bear_pivot) + pivot_offset)

    merged_top = _nan
    merged_bottom = _nan
    merged_left = _nan
    merged_bias = _nan
    merged_valid = _false

    for lane_index in range(candidate_lanes):
        lane_event = event & (((event_count - 1.0) % candidate_lanes) == lane_index)
        next_lane_event = bars_next(lane_event)
        span = fill_na(iff(lane_event, span_at_event, math.nan), "backward")
        bias_for_interval = fill_na(iff(lane_event, event_bias, math.nan), "backward")
        generation_for_interval = fill_na(iff(lane_event, generation, math.nan), "backward")
        scale_for_interval = fill_na(iff(lane_event, max(abs(c), 1.0), math.nan), "backward")
        in_interval = (~is_na(next_lane_event)) & (~is_na(span)) & (next_lane_event >= 1.0) & (next_lane_event <= span) & (next_lane_event <= _OB_SCAN)

        select_value = iff(bias_for_interval > 0, (0.0 - parsed_low) / scale_for_interval, parsed_high / scale_for_interval)
        score = generation_for_interval * _SCORE_STEP + select_value + next_lane_event * 0.000000001
        masked_score = iff(in_interval, score, 0.0 - _BIG * _SCORE_STEP)
        rolling_best = masked_score.hhv(_OB_SCAN + 1)
        best_at_event = iff(lane_event, rolling_best, math.nan)
        best_for_interval = fill_na(best_at_event, "backward")
        selected_bar = in_interval & (score == best_for_interval)
        lane_valid = lane_event & (rolling_best > (0.0 - _BIG * _SCORE_STEP * 0.5))
        lane_top = iff(lane_valid, value_when(selected_bar, parsed_high), math.nan)
        lane_bottom = iff(lane_valid, value_when(selected_bar, parsed_low), math.nan)
        lane_left = iff(lane_valid, _age(selected_bar), math.nan)

        merged_top = iff(lane_event, lane_top, merged_top)
        merged_bottom = iff(lane_event, lane_bottom, merged_bottom)
        merged_left = iff(lane_event, lane_left, merged_left)
        merged_bias = iff(lane_event, event_bias, merged_bias)
        merged_valid = merged_valid | lane_valid

    created = event & merged_valid & (~is_na(merged_top)) & (~is_na(merged_bottom)) & (~is_na(merged_left))
    return created, merged_top, merged_bottom, merged_left, merged_bias


def _build_state_slots(created_event, event_top, event_bottom, event_left, event_bias, physical_slots, close_mitigation):
    event_count = iff(created_event, 1.0, 0.0).sum(0)
    slots = []
    for slot_index in range(physical_slots):
        slot_event = created_event & (((event_count - 1.0) % physical_slots) == slot_index)
        top = value_when(slot_event, event_top)
        bottom = value_when(slot_event, event_bottom)
        left_offset = value_when(slot_event, event_left)
        bias = value_when(slot_event, event_bias)
        if close_mitigation:
            bull_broken = c < bottom
            bear_broken = c > top
        else:
            bull_broken = l < bottom
            bear_broken = h > top
        invalid = ((bias > 0) & bull_broken) | ((bias < 0) & bear_broken)
        invalid_after_creation = invalid & (~slot_event)
        age = _age(slot_event)
        active = (age < _age(invalid_after_creation)) & (~is_na(top)) & (~is_na(bottom)) & (~is_na(left_offset))
        break_event = invalid_after_creation & ref(active, 1)
        slots.append((top, bottom, bias, active, age, left_offset, break_event))
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


def _freeze_slot(slot, rank, visible_count):
    current_visible = _broadcast_last_bool(slot[3] & (rank < visible_count))
    top = _broadcast_last(slot[0])
    bottom = _broadcast_last(slot[1])
    bias = _broadcast_last(slot[2])
    event_age = _broadcast_last(slot[4])
    left_offset = _broadcast_last(slot[5])
    left_age = event_age + left_offset
    valid = current_visible & (~is_na(top)) & (~is_na(bottom)) & (~is_na(left_age))
    return top, bottom, bias, valid & (x_age <= left_age)


def _select_rank(slots, ranks, target_rank):
    top = _nan
    bottom = _nan
    bias = _nan
    exists = _false
    for index in range(len(slots)):
        match = slots[index][3] & (ranks[index] == target_rank)
        top = iff(match, slots[index][0], top)
        bottom = iff(match, slots[index][1], bottom)
        bias = iff(match, slots[index][2], bias)
        exists = exists | match
    return _broadcast_last(top), _broadcast_last(bottom), _broadcast_last(bias), _broadcast_last_bool(exists)


def _or_breaks(slots):
    result = _false
    for slot in slots:
        result = result | slot[6]
    return result


# Structure engine used by LuxAlgo to create OBs.
st_conf, sb_conf, st_level, sb_level = _swing_state(swing_length)
it_conf, ib_conf, it_level, ib_level = _swing_state(_INTERNAL_LEN)
upper_wick = h - max(c, o)
lower_wick = min(c, o) - l
if internal_confluence:
    bullish_bar = upper_wick > lower_wick
    bearish_bar = upper_wick < lower_wick
else:
    bullish_bar = _true
    bearish_bar = _true

iup = _once_after_pivot(_crossover(c, it_level) & (~is_na(it_level)) & (~is_na(st_level)) & (it_level != st_level) & bullish_bar, it_conf)
idn = _once_after_pivot(_crossunder(c, ib_level) & (~is_na(ib_level)) & (~is_na(sb_level)) & (ib_level != sb_level) & bearish_bar, ib_conf)
sup = _once_after_pivot(_crossover(c, st_level), st_conf)
sdn = _once_after_pivot(_crossunder(c, sb_level), sb_conf)

# Source volatility parsing.
true_range = max(h, ref(c, 1)) - min(l, ref(c, 1))
atr200 = true_range.smma(200, 1)
bar_index_like = max(bars_count(c) - 1.0, 1.0)
cumulative_tr = true_range.sum(0) / bar_index_like
volatility = atr200 if filter_mode == 0 else cumulative_tr
high_volatility = (h - l) >= volatility * 2.0
parsed_high = iff(high_volatility, l, h)
parsed_low = iff(high_volatility, h, l)
close_mitigation = mitigation_mode == 1

if show_internal_ob:
    i_created, i_event_top, i_event_bottom, i_event_left, i_event_bias = _select_ob_events(iup, idn, it_conf, ib_conf, _INTERNAL_LEN, parsed_high, parsed_low, _CANDIDATE_LANES)
    i_slots = _build_state_slots(i_created, i_event_top, i_event_bottom, i_event_left, i_event_bias, _STATE_SLOTS, close_mitigation)
    i_ranks = _rank_active(i_slots)
    i_frozen = [_freeze_slot(i_slots[index], i_ranks[index], internal_ob_count) for index in range(_STATE_SLOTS)]
else:
    i_created = _false
    i_event_bias = _nan
    i_slots = []
    i_ranks = []
    i_frozen = [(_nan, _nan, _nan, _false) for _ in range(_STATE_SLOTS)]

if show_swing_ob:
    s_created, s_event_top, s_event_bottom, s_event_left, s_event_bias = _select_ob_events(sup, sdn, st_conf, sb_conf, swing_length, parsed_high, parsed_low, _CANDIDATE_LANES)
    s_slots = _build_state_slots(s_created, s_event_top, s_event_bottom, s_event_left, s_event_bias, _STATE_SLOTS, close_mitigation)
    s_ranks = _rank_active(s_slots)
    s_frozen = [_freeze_slot(s_slots[index], s_ranks[index], swing_ob_count) for index in range(_STATE_SLOTS)]
else:
    s_created = _false
    s_event_bias = _nan
    s_slots = []
    s_ranks = []
    s_frozen = [(_nan, _nan, _nan, _false) for _ in range(_STATE_SLOTS)]

# Optional labels identify the three most recent current active blocks.
ob_label_gap = max(atr200 * 0.10, c * 0.0010)
i_labels = []
s_labels = []
for target in range(3):
    if show_internal_ob:
        zone = _select_rank(i_slots, i_ranks, target)
    else:
        zone = (_nan, _nan, _nan, _false)
    enabled = show_ob_labels and (ob_label_count >= target + 1)
    cond = is_last & zone[3] if enabled else _false
    y = iff(zone[2] > 0, zone[1] - ob_label_gap, zone[0] + ob_label_gap)
    color = iff(zone[2] > 0, internal_bull_text, internal_bear_text)
    i_labels.append((cond, y, color))

    if show_swing_ob:
        zone = _select_rank(s_slots, s_ranks, target)
    else:
        zone = (_nan, _nan, _nan, _false)
    cond = is_last & zone[3] if enabled else _false
    y = iff(zone[2] > 0, zone[1] - ob_label_gap, zone[0] + ob_label_gap)
    color = iff(zone[2] > 0, swing_bull_text, swing_bear_text)
    s_labels.append((cond, y, color))

i_colors = [iff(zone[2] > 0, internal_bull_fill, internal_bear_fill) for zone in i_frozen]
s_colors = [iff(zone[2] > 0, swing_bull_fill, swing_bear_fill) for zone in s_frozen]

# GLOBAL PLOTS — 46/50
plot_fillcolor("Int OB 1", i_frozen[0][0], i_frozen[0][1], i_frozen[0][3], i_colors[0], 0)
plot_fillcolor("Int OB 2", i_frozen[1][0], i_frozen[1][1], i_frozen[1][3], i_colors[1], 0)
plot_fillcolor("Int OB 3", i_frozen[2][0], i_frozen[2][1], i_frozen[2][3], i_colors[2], 0)
plot_fillcolor("Int OB 4", i_frozen[3][0], i_frozen[3][1], i_frozen[3][3], i_colors[3], 0)
plot_fillcolor("Int OB 5", i_frozen[4][0], i_frozen[4][1], i_frozen[4][3], i_colors[4], 0)
plot_fillcolor("Int OB 6", i_frozen[5][0], i_frozen[5][1], i_frozen[5][3], i_colors[5], 0)
plot_fillcolor("Int OB 7", i_frozen[6][0], i_frozen[6][1], i_frozen[6][3], i_colors[6], 0)
plot_fillcolor("Int OB 8", i_frozen[7][0], i_frozen[7][1], i_frozen[7][3], i_colors[7], 0)
plot_fillcolor("Int OB 9", i_frozen[8][0], i_frozen[8][1], i_frozen[8][3], i_colors[8], 0)
plot_fillcolor("Int OB 10", i_frozen[9][0], i_frozen[9][1], i_frozen[9][3], i_colors[9], 0)
plot_fillcolor("Int OB 11", i_frozen[10][0], i_frozen[10][1], i_frozen[10][3], i_colors[10], 0)
plot_fillcolor("Int OB 12", i_frozen[11][0], i_frozen[11][1], i_frozen[11][3], i_colors[11], 0)
plot_fillcolor("Int OB 13", i_frozen[12][0], i_frozen[12][1], i_frozen[12][3], i_colors[12], 0)
plot_fillcolor("Int OB 14", i_frozen[13][0], i_frozen[13][1], i_frozen[13][3], i_colors[13], 0)
plot_fillcolor("Int OB 15", i_frozen[14][0], i_frozen[14][1], i_frozen[14][3], i_colors[14], 0)
plot_fillcolor("Int OB 16", i_frozen[15][0], i_frozen[15][1], i_frozen[15][3], i_colors[15], 0)
plot_fillcolor("Int OB 17", i_frozen[16][0], i_frozen[16][1], i_frozen[16][3], i_colors[16], 0)
plot_fillcolor("Int OB 18", i_frozen[17][0], i_frozen[17][1], i_frozen[17][3], i_colors[17], 0)
plot_fillcolor("Int OB 19", i_frozen[18][0], i_frozen[18][1], i_frozen[18][3], i_colors[18], 0)
plot_fillcolor("Int OB 20", i_frozen[19][0], i_frozen[19][1], i_frozen[19][3], i_colors[19], 0)
plot_fillcolor("Swing OB 1", s_frozen[0][0], s_frozen[0][1], s_frozen[0][3], s_colors[0], 0)
plot_fillcolor("Swing OB 2", s_frozen[1][0], s_frozen[1][1], s_frozen[1][3], s_colors[1], 0)
plot_fillcolor("Swing OB 3", s_frozen[2][0], s_frozen[2][1], s_frozen[2][3], s_colors[2], 0)
plot_fillcolor("Swing OB 4", s_frozen[3][0], s_frozen[3][1], s_frozen[3][3], s_colors[3], 0)
plot_fillcolor("Swing OB 5", s_frozen[4][0], s_frozen[4][1], s_frozen[4][3], s_colors[4], 0)
plot_fillcolor("Swing OB 6", s_frozen[5][0], s_frozen[5][1], s_frozen[5][3], s_colors[5], 0)
plot_fillcolor("Swing OB 7", s_frozen[6][0], s_frozen[6][1], s_frozen[6][3], s_colors[6], 0)
plot_fillcolor("Swing OB 8", s_frozen[7][0], s_frozen[7][1], s_frozen[7][3], s_colors[7], 0)
plot_fillcolor("Swing OB 9", s_frozen[8][0], s_frozen[8][1], s_frozen[8][3], s_colors[8], 0)
plot_fillcolor("Swing OB 10", s_frozen[9][0], s_frozen[9][1], s_frozen[9][3], s_colors[9], 0)
plot_fillcolor("Swing OB 11", s_frozen[10][0], s_frozen[10][1], s_frozen[10][3], s_colors[10], 0)
plot_fillcolor("Swing OB 12", s_frozen[11][0], s_frozen[11][1], s_frozen[11][3], s_colors[11], 0)
plot_fillcolor("Swing OB 13", s_frozen[12][0], s_frozen[12][1], s_frozen[12][3], s_colors[12], 0)
plot_fillcolor("Swing OB 14", s_frozen[13][0], s_frozen[13][1], s_frozen[13][3], s_colors[13], 0)
plot_fillcolor("Swing OB 15", s_frozen[14][0], s_frozen[14][1], s_frozen[14][3], s_colors[14], 0)
plot_fillcolor("Swing OB 16", s_frozen[15][0], s_frozen[15][1], s_frozen[15][3], s_colors[15], 0)
plot_fillcolor("Swing OB 17", s_frozen[16][0], s_frozen[16][1], s_frozen[16][3], s_colors[16], 0)
plot_fillcolor("Swing OB 18", s_frozen[17][0], s_frozen[17][1], s_frozen[17][3], s_colors[17], 0)
plot_fillcolor("Swing OB 19", s_frozen[18][0], s_frozen[18][1], s_frozen[18][3], s_colors[18], 0)
plot_fillcolor("Swing OB 20", s_frozen[19][0], s_frozen[19][1], s_frozen[19][3], s_colors[19], 0)
plot_text("iOB tag 1", i_labels[0][0], i_labels[0][1], "iOB", i_labels[0][2], ob_label_size, 0, 0, 0)
plot_text("iOB tag 2", i_labels[1][0], i_labels[1][1], "iOB", i_labels[1][2], ob_label_size, 0, 0, 0)
plot_text("iOB tag 3", i_labels[2][0], i_labels[2][1], "iOB", i_labels[2][2], ob_label_size, 0, 0, 0)
plot_text("sOB tag 1", s_labels[0][0], s_labels[0][1], "sOB", s_labels[0][2], ob_label_size, 0, 0, 0)
plot_text("sOB tag 2", s_labels[1][0], s_labels[1][1], "sOB", s_labels[1][2], ob_label_size, 0, 0, 0)
plot_text("sOB tag 3", s_labels[2][0], s_labels[2][1], "sOB", s_labels[2][2], ob_label_size, 0, 0, 0)

output_parameter(
    internal_bull_ob_created=i_created & (i_event_bias > 0),
    internal_bear_ob_created=i_created & (i_event_bias < 0),
    swing_bull_ob_created=s_created & (s_event_bias > 0),
    swing_bear_ob_created=s_created & (s_event_bias < 0),
    internal_ob_broken=_or_breaks(i_slots),
    swing_ob_broken=_or_breaks(s_slots),
)
