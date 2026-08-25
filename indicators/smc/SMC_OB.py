# Smart Money Concepts [LuxAlgo] source-aligned port — Order Blocks module v3.2
# Target: moomoo Python custom indicator
# Source baseline: LuxAlgo open Pine v5 mirror, commit 31756c8615aff4cefe9cf97350e78bd427f663cd
# License: CC BY-NC-SA 4.0; original © LuxAlgo.
#
# Source-aligned changes from v2:
# - one chronological mixed-bias array per Internal/Swing family
# - 1..20 visible blocks per family (40 static fill channels total)
# - ATR or cumulative-true-range volatility parsing
# - Close or High/Low mitigation (source default High/Low)
# - high-volatility bars are parsed by swapping high/low, matching Pine arrays

import math
from ftool import *

indicator(
    "SMC_OB",
    "SMC Order Blocks",
    True,
    "Source-aligned current active Internal/Swing order blocks with mitigation and alpha fills.",
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
ob_label_count = input_parameter("OB Label Count 0-5", 5)
ob_label_size = input_parameter("OB Label Size 1-3", 1)

if monochrome:
    internal_bull_fill = Color.rgb(178, 181, 190, 52)
    internal_bear_fill = Color.rgb(93, 96, 107, 52)
    swing_bull_fill = Color.rgb(178, 181, 190, 52)
    swing_bear_fill = Color.rgb(93, 96, 107, 52)
else:
    internal_bull_fill = Color.rgb(49, 121, 245, 52)
    internal_bear_fill = Color.rgb(247, 124, 128, 52)
    swing_bull_fill = Color.rgb(24, 72, 204, 52)
    swing_bear_fill = Color.rgb(178, 40, 51, 52)

if monochrome:
    internal_bull_text = Color.hex("#B2B5BE")
    internal_bear_text = Color.hex("#5D606B")
    swing_bull_text = Color.hex("#B2B5BE")
    swing_bear_text = Color.hex("#5D606B")
else:
    internal_bull_text = Color.hex("#3179F5")
    internal_bear_text = Color.hex("#F77C80")
    swing_bull_text = Color.hex("#1848CC")
    swing_bear_text = Color.hex("#B22833")

o = open()
h = high()
l = low()
c = close()
_BIG = 1000000000.0
_INTERNAL_LEN = 5
_SCAN_MAX = 500
_PHYSICAL_SLOTS = 48
_VISIBLE_SLOTS = 20
_false = c != c
_true = c == c
_nan = c * math.nan
is_last = curr_bars_count(c) == 0
x_age = curr_bars_count(c)


def _age(cond):
    return replace_na(bars_last(cond), _BIG)


def _previous_age(cond):
    return replace_na(ref(bars_last(cond), 1), _BIG)


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


def _scan_order_block(pivot_confirm, pivot_offset, parsed_high, parsed_low, bearish_block):
    """Pine storeOrderBlock() slice/indexof(max|min), capped at 500 bars."""
    pivot_age = _age(pivot_confirm) + pivot_offset
    has_pivot = _age(pivot_confirm) < _BIG
    best_key = _nan
    best_top = _nan
    best_bottom = _nan
    best_offset = _nan
    for k in range(1, _SCAN_MAX + 1):
        ph = ref(parsed_high, k)
        pl = ref(parsed_low, k)
        eligible = has_pivot & (pivot_age >= k)
        if bearish_block:
            better = eligible & (is_na(best_key) | (ph >= best_key))
            key = ph
        else:
            better = eligible & (is_na(best_key) | (pl <= best_key))
            key = pl
        best_key = iff(better, key, best_key)
        best_top = iff(better, ph, best_top)
        best_bottom = iff(better, pl, best_bottom)
        best_offset = iff(better, k, best_offset)
    return best_top, best_bottom, best_offset


def _build_combined_slots(bull_event, bear_event, bull_top, bull_bottom, bull_left, bear_top, bear_bottom, bear_left, physical_slots, close_mitigation):
    event = bull_event | bear_event
    event_count = iff(event, 1.0, 0.0).sum(0)
    slots = []
    for slot_index in range(physical_slots):
        slot_event = event & (((event_count - 1.0) % physical_slots) == slot_index)
        top = value_when(slot_event, iff(bull_event, bull_top, bear_top))
        bottom = value_when(slot_event, iff(bull_event, bull_bottom, bear_bottom))
        left_offset = value_when(slot_event, iff(bull_event, bull_left, bear_left))
        bias = value_when(slot_event, iff(bull_event, 1.0, -1.0))
        if close_mitigation:
            bull_broken = c < bottom
            bear_broken = c > top
        else:
            bull_broken = l < bottom
            bear_broken = h > top
        invalid = ((bias > 0) & bull_broken) | ((bias < 0) & bear_broken)
        invalid_after_creation = invalid & (~slot_event)
        age = _age(slot_event)
        active = (age < _age(invalid_after_creation)) & (~is_na(top)) & (~is_na(bottom))
        break_event = invalid_after_creation & ref(active, 1)
        slots.append((top, bottom, bias, active, age, left_offset, break_event))
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
        left_offset = _nan
        for idx in range(len(slots)):
            match = has_zone & (remaining[idx] == best_age)
            top = iff(match, slots[idx][0], top)
            bottom = iff(match, slots[idx][1], bottom)
            bias = iff(match, slots[idx][2], bias)
            left_offset = iff(match, slots[idx][5], left_offset)
        selected.append((top, bottom, bias, has_zone, best_age, left_offset))
        next_remaining = []
        for age_value in remaining:
            next_remaining.append(iff(age_value == best_age, _BIG, age_value))
        remaining = next_remaining
    return selected


def _freeze_current(zone):
    top = fill_na(iff(is_last & zone[3], zone[0], math.nan), "backward")
    bottom = fill_na(iff(is_last & zone[3], zone[1], math.nan), "backward")
    bias = fill_na(iff(is_last & zone[3], zone[2], math.nan), "backward")
    event_age = fill_na(iff(is_last & zone[3], zone[4], math.nan), "backward")
    left_offset = fill_na(iff(is_last & zone[3], zone[5], math.nan), "backward")
    left_age = event_age + left_offset
    exists = (~is_na(top)) & (~is_na(bottom)) & (~is_na(left_age))
    visible = exists & (x_age <= left_age)
    return top, bottom, bias, visible


def _or_breaks(slots):
    result = _false
    for zone in slots:
        result = result | zone[6]
    return result


# Structure engine used by the source to trigger OB creation.
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

# Bullish structure stores a bullish OB at the minimum parsedLow; bearish at max parsedHigh.
# Skip unused family scans; Pine also stores only when that OB family is enabled.
if show_internal_ob:
    i_bull_top, i_bull_bottom, i_bull_left = _scan_order_block(it_conf, _INTERNAL_LEN, parsed_high, parsed_low, False)
    i_bear_top, i_bear_bottom, i_bear_left = _scan_order_block(ib_conf, _INTERNAL_LEN, parsed_high, parsed_low, True)
    i_bull_event = iup & (~is_na(i_bull_bottom))
    i_bear_event = idn & (~is_na(i_bear_top))
else:
    i_bull_top = _nan
    i_bull_bottom = _nan
    i_bull_left = _nan
    i_bear_top = _nan
    i_bear_bottom = _nan
    i_bear_left = _nan
    i_bull_event = _false
    i_bear_event = _false

if show_swing_ob:
    s_bull_top, s_bull_bottom, s_bull_left = _scan_order_block(st_conf, swing_length, parsed_high, parsed_low, False)
    s_bear_top, s_bear_bottom, s_bear_left = _scan_order_block(sb_conf, swing_length, parsed_high, parsed_low, True)
    s_bull_event = sup & (~is_na(s_bull_bottom))
    s_bear_event = sdn & (~is_na(s_bear_top))
else:
    s_bull_top = _nan
    s_bull_bottom = _nan
    s_bull_left = _nan
    s_bear_top = _nan
    s_bear_bottom = _nan
    s_bear_left = _nan
    s_bull_event = _false
    s_bear_event = _false

close_mitigation = mitigation_mode == 1
i_slots = _build_combined_slots(i_bull_event, i_bear_event, i_bull_top, i_bull_bottom, i_bull_left, i_bear_top, i_bear_bottom, i_bear_left, _PHYSICAL_SLOTS, close_mitigation)
s_slots = _build_combined_slots(s_bull_event, s_bear_event, s_bull_top, s_bull_bottom, s_bull_left, s_bear_top, s_bear_bottom, s_bear_left, _PHYSICAL_SLOTS, close_mitigation)
i_selected = [_freeze_current(zone) for zone in _recent_active(i_slots, _VISIBLE_SLOTS)]
s_selected = [_freeze_current(zone) for zone in _recent_active(s_slots, _VISIBLE_SLOTS)]

i_visible = []
s_visible = []
i_colors = []
s_colors = []
for idx in range(_VISIBLE_SLOTS):
    i_enabled = show_internal_ob and (internal_ob_count >= idx + 1)
    s_enabled = show_swing_ob and (swing_ob_count >= idx + 1)
    i_visible.append(i_selected[idx][3] if i_enabled else _false)
    s_visible.append(s_selected[idx][3] if s_enabled else _false)
    i_colors.append(iff(i_selected[idx][2] > 0, internal_bull_fill, internal_bear_fill))
    s_colors.append(iff(s_selected[idx][2] > 0, swing_bull_fill, swing_bear_fill))

# Labels are placed at the current/right edge.  The 50-plot platform ceiling
# allows labels for the five most recent Internal and Swing blocks.
ob_label_gap = max(atr200 * 0.10, c * 0.0010)
i_label_cond = []
s_label_cond = []
i_label_y = []
s_label_y = []
i_label_color = []
s_label_color = []
for idx in range(5):
    i_enabled = show_ob_labels and (ob_label_count >= idx + 1)
    s_enabled = show_ob_labels and (ob_label_count >= idx + 1)
    i_label_cond.append((is_last & i_visible[idx]) if i_enabled else _false)
    s_label_cond.append((is_last & s_visible[idx]) if s_enabled else _false)
    i_label_y.append(iff(i_selected[idx][2] > 0, i_selected[idx][1] - ob_label_gap, i_selected[idx][0] + ob_label_gap))
    s_label_y.append(iff(s_selected[idx][2] > 0, s_selected[idx][1] - ob_label_gap, s_selected[idx][0] + ob_label_gap))
    i_label_color.append(iff(i_selected[idx][2] > 0, internal_bull_text, internal_bear_text))
    s_label_color.append(iff(s_selected[idx][2] > 0, swing_bull_text, swing_bear_text))

# GLOBAL PLOTS — 50/50
plot_fillcolor("Int OB 1", i_selected[0][0], i_selected[0][1], i_visible[0], i_colors[0], 0)
plot_fillcolor("Int OB 2", i_selected[1][0], i_selected[1][1], i_visible[1], i_colors[1], 0)
plot_fillcolor("Int OB 3", i_selected[2][0], i_selected[2][1], i_visible[2], i_colors[2], 0)
plot_fillcolor("Int OB 4", i_selected[3][0], i_selected[3][1], i_visible[3], i_colors[3], 0)
plot_fillcolor("Int OB 5", i_selected[4][0], i_selected[4][1], i_visible[4], i_colors[4], 0)
plot_fillcolor("Int OB 6", i_selected[5][0], i_selected[5][1], i_visible[5], i_colors[5], 0)
plot_fillcolor("Int OB 7", i_selected[6][0], i_selected[6][1], i_visible[6], i_colors[6], 0)
plot_fillcolor("Int OB 8", i_selected[7][0], i_selected[7][1], i_visible[7], i_colors[7], 0)
plot_fillcolor("Int OB 9", i_selected[8][0], i_selected[8][1], i_visible[8], i_colors[8], 0)
plot_fillcolor("Int OB 10", i_selected[9][0], i_selected[9][1], i_visible[9], i_colors[9], 0)
plot_fillcolor("Int OB 11", i_selected[10][0], i_selected[10][1], i_visible[10], i_colors[10], 0)
plot_fillcolor("Int OB 12", i_selected[11][0], i_selected[11][1], i_visible[11], i_colors[11], 0)
plot_fillcolor("Int OB 13", i_selected[12][0], i_selected[12][1], i_visible[12], i_colors[12], 0)
plot_fillcolor("Int OB 14", i_selected[13][0], i_selected[13][1], i_visible[13], i_colors[13], 0)
plot_fillcolor("Int OB 15", i_selected[14][0], i_selected[14][1], i_visible[14], i_colors[14], 0)
plot_fillcolor("Int OB 16", i_selected[15][0], i_selected[15][1], i_visible[15], i_colors[15], 0)
plot_fillcolor("Int OB 17", i_selected[16][0], i_selected[16][1], i_visible[16], i_colors[16], 0)
plot_fillcolor("Int OB 18", i_selected[17][0], i_selected[17][1], i_visible[17], i_colors[17], 0)
plot_fillcolor("Int OB 19", i_selected[18][0], i_selected[18][1], i_visible[18], i_colors[18], 0)
plot_fillcolor("Int OB 20", i_selected[19][0], i_selected[19][1], i_visible[19], i_colors[19], 0)
plot_fillcolor("Swing OB 1", s_selected[0][0], s_selected[0][1], s_visible[0], s_colors[0], 0)
plot_fillcolor("Swing OB 2", s_selected[1][0], s_selected[1][1], s_visible[1], s_colors[1], 0)
plot_fillcolor("Swing OB 3", s_selected[2][0], s_selected[2][1], s_visible[2], s_colors[2], 0)
plot_fillcolor("Swing OB 4", s_selected[3][0], s_selected[3][1], s_visible[3], s_colors[3], 0)
plot_fillcolor("Swing OB 5", s_selected[4][0], s_selected[4][1], s_visible[4], s_colors[4], 0)
plot_fillcolor("Swing OB 6", s_selected[5][0], s_selected[5][1], s_visible[5], s_colors[5], 0)
plot_fillcolor("Swing OB 7", s_selected[6][0], s_selected[6][1], s_visible[6], s_colors[6], 0)
plot_fillcolor("Swing OB 8", s_selected[7][0], s_selected[7][1], s_visible[7], s_colors[7], 0)
plot_fillcolor("Swing OB 9", s_selected[8][0], s_selected[8][1], s_visible[8], s_colors[8], 0)
plot_fillcolor("Swing OB 10", s_selected[9][0], s_selected[9][1], s_visible[9], s_colors[9], 0)
plot_fillcolor("Swing OB 11", s_selected[10][0], s_selected[10][1], s_visible[10], s_colors[10], 0)
plot_fillcolor("Swing OB 12", s_selected[11][0], s_selected[11][1], s_visible[11], s_colors[11], 0)
plot_fillcolor("Swing OB 13", s_selected[12][0], s_selected[12][1], s_visible[12], s_colors[12], 0)
plot_fillcolor("Swing OB 14", s_selected[13][0], s_selected[13][1], s_visible[13], s_colors[13], 0)
plot_fillcolor("Swing OB 15", s_selected[14][0], s_selected[14][1], s_visible[14], s_colors[14], 0)
plot_fillcolor("Swing OB 16", s_selected[15][0], s_selected[15][1], s_visible[15], s_colors[15], 0)
plot_fillcolor("Swing OB 17", s_selected[16][0], s_selected[16][1], s_visible[16], s_colors[16], 0)
plot_fillcolor("Swing OB 18", s_selected[17][0], s_selected[17][1], s_visible[17], s_colors[17], 0)
plot_fillcolor("Swing OB 19", s_selected[18][0], s_selected[18][1], s_visible[18], s_colors[18], 0)
plot_fillcolor("Swing OB 20", s_selected[19][0], s_selected[19][1], s_visible[19], s_colors[19], 0)

plot_text("iOB tag 1", i_label_cond[0], i_label_y[0], "iOB", i_label_color[0], ob_label_size, 0, 0, 0)
plot_text("iOB tag 2", i_label_cond[1], i_label_y[1], "iOB", i_label_color[1], ob_label_size, 0, 0, 0)
plot_text("iOB tag 3", i_label_cond[2], i_label_y[2], "iOB", i_label_color[2], ob_label_size, 0, 0, 0)
plot_text("iOB tag 4", i_label_cond[3], i_label_y[3], "iOB", i_label_color[3], ob_label_size, 0, 0, 0)
plot_text("iOB tag 5", i_label_cond[4], i_label_y[4], "iOB", i_label_color[4], ob_label_size, 0, 0, 0)
plot_text("sOB tag 1", s_label_cond[0], s_label_y[0], "sOB", s_label_color[0], ob_label_size, 0, 0, 0)
plot_text("sOB tag 2", s_label_cond[1], s_label_y[1], "sOB", s_label_color[1], ob_label_size, 0, 0, 0)
plot_text("sOB tag 3", s_label_cond[2], s_label_y[2], "sOB", s_label_color[2], ob_label_size, 0, 0, 0)
plot_text("sOB tag 4", s_label_cond[3], s_label_y[3], "sOB", s_label_color[3], ob_label_size, 0, 0, 0)
plot_text("sOB tag 5", s_label_cond[4], s_label_y[4], "sOB", s_label_color[4], ob_label_size, 0, 0, 0)

output_parameter(
    internal_bull_ob_created=i_bull_event,
    internal_bear_ob_created=i_bear_event,
    swing_bull_ob_created=s_bull_event,
    swing_bear_ob_created=s_bear_event,
    internal_ob_broken=_or_breaks(i_slots),
    swing_ob_broken=_or_breaks(s_slots),
)
