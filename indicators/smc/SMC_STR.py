# Smart Money Concepts [LuxAlgo] source-aligned port — Structure module v3.2
# Target: moomoo Python custom indicator
# Source baseline: LuxAlgo open Pine v5 mirror, commit 31756c8615aff4cefe9cf97350e78bd427f663cd
# License: CC BY-NC-SA 4.0; original © LuxAlgo. This port preserves attribution.
#
# Client-confirmed moomoo constraints:
# - all plot_* calls at module/global scope
# - <= 50 plot calls per indicator
# - plot name <= 25 chars
# - plot_stickline has 9 positional args
# - disconnected plot() runs are joined; independent segments use plot_stickline

import math
from ftool import *

indicator(
    "SMC_STR",
    "SMC Structure",
    True,
    "Source-aligned Internal/Swing structure with corrected pivot-to-break geometry, EQH/EQL and trailing Strong/Weak levels.",
)

# -----------------------------------------------------------------------------
# Pine input mapping. Integer selectors are used because moomoo input_parameter
# does not expose Pine-style dropdown option metadata.
# 0=All, 1=BOS only, 2=CHoCH only.
# -----------------------------------------------------------------------------
present_mode = input_parameter("Mode: Present", False)  # Pine default: Historical
monochrome = input_parameter("Style: Monochrome", False)  # Pine default: Colored
color_candles = input_parameter("Color Candles", False)

show_internal = input_parameter("Show Internal Structure", True)
internal_bull_mode = input_parameter("Internal Bull 0All1BOS2CH", 0)
internal_bear_mode = input_parameter("Internal Bear 0All1BOS2CH", 0)
internal_confluence = input_parameter("Confluence Filter", False)
internal_label_size = input_parameter("Internal Label Size 1-3", 1)

show_swing = input_parameter("Show Swing Structure", True)
swing_bull_mode = input_parameter("Swing Bull 0All1BOS2CH", 0)
swing_bear_mode = input_parameter("Swing Bear 0All1BOS2CH", 0)
swing_label_size = input_parameter("Swing Label Size 1-3", 2)
show_swing_points = input_parameter("Show Swing Points", False)
swing_length = input_parameter("Swing Length", 50)
show_strong_weak = input_parameter("Show Strong/Weak H/L", True)

show_eqhl = input_parameter("Equal High/Low", True)
eq_length = input_parameter("EQ Bars Confirmation", 3)
eq_threshold = input_parameter("EQ Threshold", 0.10)
eq_label_size = input_parameter("EQ Label Size 1-3", 1)

# Visual spacing controls. Values are ATR(200) multiples; increase them if
# labels still overlap lines/candles on a particular symbol or timeframe.
internal_label_gap_atr = input_parameter("Internal Label Gap ATR", 0.30)
swing_label_gap_atr = input_parameter("Swing Label Gap ATR", 0.40)
eq_label_gap_atr = input_parameter("EQ Label Gap ATR", 0.30)
strongweak_gap_atr = input_parameter("StrongWeak Gap ATR", 0.35)

# moomoo sequence engine has no dynamic unbounded array/object state. 500 is the
# explicit fidelity scan horizon for trailing extremes, matching the legacy
# LuxAlgo max_bars_back reference and covering normal chart history.
_TRAIL_SCAN = 500
_INTERNAL_LEN = 5
_BIG = 1000000000.0

# -----------------------------------------------------------------------------
# Colors (LuxAlgo defaults)
# -----------------------------------------------------------------------------
if monochrome:
    bull = Color.hex("#B2B5BE")
    bear = Color.hex("#5D606B")
else:
    bull = Color.hex("#089981")
    bear = Color.hex("#F23645")
ibull = bull
ibear = bear
neutral = Color.hex("#878B94")

# -----------------------------------------------------------------------------
# Series
# -----------------------------------------------------------------------------
o = open()
h = high()
l = low()
c = close()
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
    """Vector equivalent of LuxAlgo leg(size)/getCurrentStructure()."""
    new_leg_high = ref(h, length) > h.hhv(length)
    new_leg_low = (ref(l, length) < l.llv(length)) & (~new_leg_high)

    prev_high_age = replace_na(ref(bars_last(new_leg_high), 1), _BIG)
    prev_low_age = replace_na(ref(bars_last(new_leg_low), 1), _BIG)
    previous_leg_is_bearish = prev_high_age <= prev_low_age

    top_confirm = new_leg_high & (~previous_leg_is_bearish)
    bottom_confirm = new_leg_low & previous_leg_is_bearish

    top_value = ref(h, length)
    bottom_value = ref(l, length)
    top_level = value_when(top_confirm, top_value)
    bottom_level = value_when(bottom_confirm, bottom_value)

    # Actual pivot anchors, back-painted to bar_index-size.
    top_anchor = filter(backset(top_confirm, length + 1), length)
    bottom_anchor = filter(backset(bottom_confirm, length + 1), length)
    return top_confirm, bottom_confirm, top_value, bottom_value, top_level, bottom_level, top_anchor, bottom_anchor


def _crossover(x, y):
    return (x > y) & (ref(x, 1) <= ref(y, 1))


def _crossunder(x, y):
    return (x < y) & (ref(x, 1) >= ref(y, 1))


def _once_after_pivot(raw_break, pivot_confirm):
    # Reproduces pivot.crossed: one valid breakout per current pivot.
    return raw_break & (_age(pivot_confirm) <= _previous_age(raw_break))


def _classify(bull_break, bear_break):
    """Sequential Pine-equivalent BOS/CHoCH classification.

    Pine stores an explicit trend bias.  Using the previous event direction is
    more robust than inferring bias from bars_last() ages, especially near the
    beginning of chart history.  If both directions were ever true on one bar,
    Pine evaluates bullish first and bearish second, so bearish wins final bias.
    """
    any_break = bull_break | bear_break
    event_direction = iff(bear_break, -1.0, iff(bull_break, 1.0, math.nan))
    previous_bias = replace_na(ref(value_when(any_break, event_direction), 1), 0.0)

    bull_choch = bull_break & (previous_bias == -1.0)
    bull_bos = bull_break & (~bull_choch)

    bias_after_bull = iff(bull_break, 1.0, previous_bias)
    bear_choch = bear_break & (bias_after_bull == 1.0)
    bear_bos = bear_break & (~bear_choch)

    current_bias = replace_na(value_when(any_break, event_direction), 0.0)
    trend_up = current_bias == 1.0
    trend_down = current_bias == -1.0
    return bull_bos, bull_choch, bear_bos, bear_choch, trend_up, trend_down


def _filter_pair(bos_event, choch_event, mode_value):
    if mode_value == 1:
        return bos_event, _false
    if mode_value == 2:
        return _false, choch_event
    return bos_event, choch_event


def _history_structure_segment(event, pivot_confirm, pivot_offset, level):
    """Render the exact Pine pivot-bar -> break-bar historical segment.

    Pine stores pivot.barIndex at confirmation_bar - pivot_offset.  Rebuilding
    the span as age(pivot_confirm) + pivot_offset avoids relying on a repainted
    anchor series, which could shorten a segment in the moomoo runtime.
    """
    next_event = bars_next(event)
    span_at_event = _age(pivot_confirm) + pivot_offset
    span = fill_na(iff(event, span_at_event, math.nan), "backward")
    future_level = fill_na(iff(event, level, math.nan), "backward")
    visible = (~is_na(next_event)) & (~is_na(span)) & (next_event <= span)
    line_value = iff(visible, future_level, math.nan)
    # Pine math.round((pivot_index + break_index) / 2): distance from break is floor(span/2).
    midpoint = visible & (next_event * 2 <= span) & (next_event * 2 > span - 2)
    return line_value, midpoint, future_level



def _present_structure_segment(event, span_at_event, level):
    event_age = _broadcast_last(_age(event))
    span = _broadcast_last(value_when(event, span_at_event))
    current_level = _broadcast_last(value_when(event, level))
    visible = (~is_na(current_level)) & (~is_na(span)) & (x_age >= event_age) & (x_age <= event_age + span)
    line_value = iff(visible, current_level, math.nan)
    from_break = x_age - event_age
    midpoint = visible & (from_break * 2 <= span) & (from_break * 2 > span - 2)
    return line_value, midpoint, current_level

def _history_equal_segment(event, current_level, previous_level, span_at_event, confirmation_offset):
    """Pine drawEqualHighLow(): previous pivot -> current pivot, dotted."""
    next_event = bars_next(event)
    span = fill_na(iff(event, span_at_event, math.nan), "backward")
    current_y = fill_na(iff(event, current_level, math.nan), "backward")
    previous_y = fill_na(iff(event, previous_level, math.nan), "backward")
    from_current_pivot = next_event - confirmation_offset
    visible = (~is_na(next_event)) & (~is_na(span)) & (from_current_pivot >= 0) & (from_current_pivot <= span)
    safe_span = max(span, 1.0)
    line_value = current_y + (previous_y - current_y) * from_current_pivot / safe_span
    line_value = iff(visible, line_value, math.nan)
    midpoint = visible & (from_current_pivot * 2 >= span) & (from_current_pivot * 2 < span + 2)
    label_y = (current_y + previous_y) / 2.0
    return line_value, midpoint, label_y


def _present_equal_segment(event, current_level, previous_level, span_at_event, confirmation_offset):
    event_age = _broadcast_last(_age(event))
    span = _broadcast_last(value_when(event, span_at_event))
    current_y = _broadcast_last(value_when(event, current_level))
    previous_y = _broadcast_last(value_when(event, previous_level))
    current_pivot_age = event_age + confirmation_offset
    from_current_pivot = x_age - current_pivot_age
    visible = (~is_na(current_y)) & (~is_na(previous_y)) & (from_current_pivot >= 0) & (from_current_pivot <= span)
    safe_span = max(span, 1.0)
    line_value = current_y + (previous_y - current_y) * from_current_pivot / safe_span
    line_value = iff(visible, line_value, math.nan)
    midpoint = visible & (from_current_pivot * 2 >= span) & (from_current_pivot * 2 < span + 2)
    return line_value, midpoint, (current_y + previous_y) / 2.0


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


# ATR measure used by LuxAlgo EQH/EQL threshold and visual offsets.
true_range = max(h, ref(c, 1)) - min(l, ref(c, 1))
atr200 = true_range.smma(200, 1)

# -----------------------------------------------------------------------------
# Internal and swing structure
# -----------------------------------------------------------------------------
st_conf, sb_conf, st_value, sb_value, st_level, sb_level, st_anchor, sb_anchor = _swing_state(swing_length)
it_conf, ib_conf, it_value, ib_value, it_level, ib_level, it_anchor, ib_anchor = _swing_state(_INTERNAL_LEN)

upper_wick = h - max(c, o)
lower_wick = min(c, o) - l
if internal_confluence:
    bullish_bar = upper_wick > lower_wick
    bearish_bar = upper_wick < lower_wick
else:
    bullish_bar = _true
    bearish_bar = _true

raw_iup = _crossover(c, it_level)
raw_idn = _crossunder(c, ib_level)
# Pine comparisons against na evaluate as false.  Explicit validity guards stop
# early-chart internal breaks from polluting the trend state before swing pivots exist.
internal_high_distinct = (~is_na(it_level)) & (~is_na(st_level)) & (it_level != st_level)
internal_low_distinct = (~is_na(ib_level)) & (~is_na(sb_level)) & (ib_level != sb_level)
iup = _once_after_pivot(raw_iup & internal_high_distinct & bullish_bar, it_conf)
idn = _once_after_pivot(raw_idn & internal_low_distinct & bearish_bar, ib_conf)
sup = _once_after_pivot(_crossover(c, st_level), st_conf)
sdn = _once_after_pivot(_crossunder(c, sb_level), sb_conf)

raw_iubos, raw_iuch, raw_idbos, raw_idch, itrend_up, itrend_down = _classify(iup, idn)
raw_subos, raw_such, raw_sdbos, raw_sdch, strend_up, strend_down = _classify(sup, sdn)

iubos, iuch = _filter_pair(raw_iubos, raw_iuch, internal_bull_mode)
idbos, idch = _filter_pair(raw_idbos, raw_idch, internal_bear_mode)
subos, such = _filter_pair(raw_subos, raw_such, swing_bull_mode)
sdbos, sdch = _filter_pair(raw_sdbos, raw_sdch, swing_bear_mode)

if not show_internal:
    iubos = _false
    iuch = _false
    idbos = _false
    idch = _false
if not show_swing:
    subos = _false
    such = _false
    sdbos = _false
    sdch = _false

int_bull_event = iubos | iuch
int_bear_event = idbos | idch
swing_bull_event = subos | such
swing_bear_event = sdbos | sdch

# Historical source-to-break geometry.
i_bull_hist, _, _ = _history_structure_segment(int_bull_event, it_conf, _INTERNAL_LEN, it_level)
i_bear_hist, _, _ = _history_structure_segment(int_bear_event, ib_conf, _INTERNAL_LEN, ib_level)
s_bull_hist, _, _ = _history_structure_segment(swing_bull_event, st_conf, swing_length, st_level)
s_bear_hist, _, _ = _history_structure_segment(swing_bear_event, sb_conf, swing_length, sb_level)
_, miubos, yiubos = _history_structure_segment(iubos, it_conf, _INTERNAL_LEN, it_level)
_, miuch, yiuch = _history_structure_segment(iuch, it_conf, _INTERNAL_LEN, it_level)
_, midbos, yidbos = _history_structure_segment(idbos, ib_conf, _INTERNAL_LEN, ib_level)
_, midch, yidch = _history_structure_segment(idch, ib_conf, _INTERNAL_LEN, ib_level)
_, msubos, ysubos = _history_structure_segment(subos, st_conf, swing_length, st_level)
_, msuch, ysuch = _history_structure_segment(such, st_conf, swing_length, st_level)
_, msdbos, ysdbos = _history_structure_segment(sdbos, sb_conf, swing_length, sb_level)
_, msdch, ysdch = _history_structure_segment(sdch, sb_conf, swing_length, sb_level)

if present_mode:
    # Pine Present mode deletes the prior line/label object; it does not extend
    # the retained segment from the break bar to the current bar.
    i_any = int_bull_event | int_bear_event
    s_any = swing_bull_event | swing_bear_event
    i_span_at_event = iff(int_bull_event, _age(it_conf) + _INTERNAL_LEN, _age(ib_conf) + _INTERNAL_LEN)
    s_span_at_event = iff(swing_bull_event, _age(st_conf) + swing_length, _age(sb_conf) + swing_length)
    i_level = iff(int_bull_event, it_level, ib_level)
    s_level = iff(swing_bull_event, st_level, sb_level)
    i_line, i_mid, i_y = _present_structure_segment(i_any, i_span_at_event, i_level)
    s_line, s_mid, s_y = _present_structure_segment(s_any, s_span_at_event, s_level)
    i_latest_bull = _broadcast_last_bool(_age(int_bull_event) < _age(int_bear_event))
    s_latest_bull = _broadcast_last_bool(_age(swing_bull_event) < _age(swing_bear_event))
    i_bull_draw = iff(i_latest_bull, i_line, math.nan)
    i_bear_draw = iff(~i_latest_bull, i_line, math.nan)
    s_bull_draw = iff(s_latest_bull, s_line, math.nan)
    s_bear_draw = iff(~s_latest_bull, s_line, math.nan)

    i_min = min(_age(iubos), _age(iuch), _age(idbos), _age(idch))
    s_min = min(_age(subos), _age(such), _age(sdbos), _age(sdch))
    i_min_last = _broadcast_last(i_min)
    s_min_last = _broadcast_last(s_min)
    viubos = i_mid & (i_min_last < _BIG) & (_broadcast_last(_age(iubos)) == i_min_last)
    viuch = i_mid & (i_min_last < _BIG) & (_broadcast_last(_age(iuch)) == i_min_last)
    vidbos = i_mid & (i_min_last < _BIG) & (_broadcast_last(_age(idbos)) == i_min_last)
    vidch = i_mid & (i_min_last < _BIG) & (_broadcast_last(_age(idch)) == i_min_last)
    vsubos = s_mid & (s_min_last < _BIG) & (_broadcast_last(_age(subos)) == s_min_last)
    vsuch = s_mid & (s_min_last < _BIG) & (_broadcast_last(_age(such)) == s_min_last)
    vsdbos = s_mid & (s_min_last < _BIG) & (_broadcast_last(_age(sdbos)) == s_min_last)
    vsdch = s_mid & (s_min_last < _BIG) & (_broadcast_last(_age(sdch)) == s_min_last)
    yiubos = i_y
    yiuch = i_y
    yidbos = i_y
    yidch = i_y
    ysubos = s_y
    ysuch = s_y
    ysdbos = s_y
    ysdch = s_y
else:
    i_bull_draw = i_bull_hist
    i_bear_draw = i_bear_hist
    s_bull_draw = s_bull_hist
    s_bear_draw = s_bear_hist
    viubos = miubos
    viuch = miuch
    vidbos = midbos
    vidch = midch
    vsubos = msubos
    vsuch = msuch
    vsdbos = msdbos
    vsdch = msdch

# -----------------------------------------------------------------------------
# Swing point labels: source defaults Show Swings Points = false.
# -----------------------------------------------------------------------------
previous_top = ref(value_when(st_anchor, h), 1)
previous_bottom = ref(value_when(sb_anchor, l), 1)
hh = st_anchor & (~is_na(previous_top)) & (h > previous_top)
lh = st_anchor & (~is_na(previous_top)) & (h <= previous_top)
ll = sb_anchor & (~is_na(previous_bottom)) & (l < previous_bottom)
hl = sb_anchor & (~is_na(previous_bottom)) & (l >= previous_bottom)
if not show_swing_points:
    hh = _false
    lh = _false
    ll = _false
    hl = _false

# -----------------------------------------------------------------------------
# Equal Highs / Lows: same leg(size) pivot engine as the Pine source.
# -----------------------------------------------------------------------------
et_conf, eb_conf, et_value, eb_value, et_level, eb_level, et_anchor, eb_anchor = _swing_state(eq_length)
previous_eq_top = ref(value_when(et_conf, et_value), 1)
previous_eq_bottom = ref(value_when(eb_conf, eb_value), 1)
eq_top_span = _previous_age(et_conf) + 1.0
eq_bottom_span = _previous_age(eb_conf) + 1.0
eqh_raw = et_conf & (~is_na(previous_eq_top)) & (abs(previous_eq_top - et_value) < eq_threshold * atr200)
eql_raw = eb_conf & (~is_na(previous_eq_bottom)) & (abs(previous_eq_bottom - eb_value) < eq_threshold * atr200)
if show_eqhl:
    eqh = eqh_raw
    eql = eql_raw
else:
    eqh = _false
    eql = _false

if present_mode:
    eqh_line, eqh_mid, eqh_y = _present_equal_segment(eqh, et_value, previous_eq_top, eq_top_span, eq_length)
    eql_line, eql_mid, eql_y = _present_equal_segment(eql, eb_value, previous_eq_bottom, eq_bottom_span, eq_length)
else:
    eqh_line, eqh_mid, eqh_y = _history_equal_segment(eqh, et_value, previous_eq_top, eq_top_span, eq_length)
    eql_line, eql_mid, eql_y = _history_equal_segment(eql, eb_value, previous_eq_bottom, eq_bottom_span, eq_length)

# -----------------------------------------------------------------------------
# Source-aligned trailing extremes for Strong/Weak H/L.
# -----------------------------------------------------------------------------
trailing_top_raw, trailing_top_offset_raw, top_start_age = _scan_extreme_since(st_conf, swing_length, h, True)
trailing_bottom_raw, trailing_bottom_offset_raw, bottom_start_age = _scan_extreme_since(sb_conf, swing_length, l, False)
trailing_top = _broadcast_last(trailing_top_raw)
trailing_bottom = _broadcast_last(trailing_bottom_raw)
trailing_top_offset = _broadcast_last(trailing_top_offset_raw)
trailing_bottom_offset = _broadcast_last(trailing_bottom_offset_raw)
top_exists = (~is_na(trailing_top)) & (~is_na(trailing_top_offset))
bottom_exists = (~is_na(trailing_bottom)) & (~is_na(trailing_bottom_offset))
top_line_visible = top_exists & (x_age <= trailing_top_offset)
bottom_line_visible = bottom_exists & (x_age <= trailing_bottom_offset)

has_swing_bias = min(_age(sup), _age(sdn)) < _BIG
swing_bias_bull = has_swing_bias & (_age(sup) < _age(sdn))
swing_bias_bear = has_swing_bias & (_age(sdn) < _age(sup))
weak_high = is_last & top_exists & (~swing_bias_bear)
strong_high = is_last & top_exists & swing_bias_bear
strong_low = is_last & bottom_exists & swing_bias_bull
weak_low = is_last & bottom_exists & (~swing_bias_bull)
if not show_strong_weak:
    top_line_visible = _false
    bottom_line_visible = _false
    weak_high = _false
    strong_high = _false
    strong_low = _false
    weak_low = _false

# -----------------------------------------------------------------------------
# Visual geometry
# -----------------------------------------------------------------------------
segment_half = max(atr200 * 0.004, c * 0.00002)
int_gap = max(atr200 * internal_label_gap_atr, c * 0.0020)
swing_gap = max(atr200 * swing_label_gap_atr, c * 0.0025)
eq_gap = max(atr200 * eq_label_gap_atr, c * 0.0020)
strong_gap = max(atr200 * strongweak_gap_atr, c * 0.0025)
point_gap = max(atr200 * 0.16, c * 0.0012)

# -----------------------------------------------------------------------------
# GLOBAL PLOTS — 28/50
# -----------------------------------------------------------------------------
plot_stickline("Int bull seg", ~is_na(i_bull_draw), i_bull_draw - segment_half, i_bull_draw + segment_half, 0.42, False, False, ibull, 0)
plot_stickline("Int bear seg", ~is_na(i_bear_draw), i_bear_draw - segment_half, i_bear_draw + segment_half, 0.42, False, False, ibear, 0)
plot_text("Int bull BOS", viubos, yiubos + int_gap, "BOS", ibull, internal_label_size, 0, 0, 0)
plot_text("Int bull CHoCH", viuch, yiuch + int_gap, "CHoCH", ibull, internal_label_size, 0, 0, 0)
plot_text("Int bear BOS", vidbos, yidbos - int_gap, "BOS", ibear, internal_label_size, 0, 0, 0)
plot_text("Int bear CHoCH", vidch, yidch - int_gap, "CHoCH", ibear, internal_label_size, 0, 0, 0)

plot_stickline("Swing bull seg", ~is_na(s_bull_draw), s_bull_draw - segment_half, s_bull_draw + segment_half, 0.95, False, False, bull, 0)
plot_stickline("Swing bear seg", ~is_na(s_bear_draw), s_bear_draw - segment_half, s_bear_draw + segment_half, 0.95, False, False, bear, 0)
plot_text("Swing bull BOS", vsubos, ysubos + swing_gap, "BOS", bull, swing_label_size, 0, 0, 0)
plot_text("Swing bull CHoCH", vsuch, ysuch + swing_gap, "CHoCH", bull, swing_label_size, 0, 0, 0)
plot_text("Swing bear BOS", vsdbos, ysdbos - swing_gap, "BOS", bear, swing_label_size, 0, 0, 0)
plot_text("Swing bear CHoCH", vsdch, ysdch - swing_gap, "CHoCH", bear, swing_label_size, 0, 0, 0)

plot_text("HH", hh, h + point_gap, "HH", bear, 2, 0, 0, 0)
plot_text("LH", lh, h + point_gap, "LH", bear, 2, 0, 0, 0)
plot_text("LL", ll, l - point_gap, "LL", bull, 2, 0, 0, 0)
plot_text("HL", hl, l - point_gap, "HL", bull, 2, 0, 0, 0)

plot_stickline("EQH seg", ~is_na(eqh_line), eqh_line - segment_half, eqh_line + segment_half, 0.30, False, False, bear, 0)
plot_stickline("EQL seg", ~is_na(eql_line), eql_line - segment_half, eql_line + segment_half, 0.30, False, False, bull, 0)
plot_text("EQH", eqh_mid, eqh_y + eq_gap, "EQH", bear, eq_label_size, 0, 0, 0)
plot_text("EQL", eql_mid, eql_y - eq_gap, "EQL", bull, eq_label_size, 0, 0, 0)

plot_stickline("Trail high", top_line_visible, trailing_top - segment_half, trailing_top + segment_half, 0.95, False, False, bear, 0)
plot_stickline("Trail low", bottom_line_visible, trailing_bottom - segment_half, trailing_bottom + segment_half, 0.95, False, False, bull, 0)
plot_text("Weak High", weak_high, trailing_top + strong_gap, "Weak High", bear, 1, 0, 0, 0)
plot_text("Strong High", strong_high, trailing_top + strong_gap, "Strong High", bear, 1, 0, 0, 0)
plot_text("Strong Low", strong_low, trailing_bottom - strong_gap, "Strong Low", bull, 1, 0, 0, 0)
plot_text("Weak Low", weak_low, trailing_bottom - strong_gap, "Weak Low", bull, 1, 0, 0, 0)

trend_color = iff(itrend_up, bull, iff(itrend_down, bear, neutral))
candle_cond = _true if color_candles else _false
plot_stickline("SMC wick", candle_cond, l, h, 0.10, False, False, trend_color, 0)
plot_stickline("SMC body", candle_cond, min(o, c), max(o, c), 0.65, False, False, trend_color, 0)

output_parameter(
    internal_bull_bos=raw_iubos,
    internal_bull_choch=raw_iuch,
    internal_bear_bos=raw_idbos,
    internal_bear_choch=raw_idch,
    swing_bull_bos=raw_subos,
    swing_bull_choch=raw_such,
    swing_bear_bos=raw_sdbos,
    swing_bear_choch=raw_sdch,
    equal_highs=eqh_raw,
    equal_lows=eql_raw,
)
