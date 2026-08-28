# Smart Money Fibonacci OTE Engine [ChartPrime] — moomoo Python port v4.1 source-fidelity pass
# Target: moomoo Python custom indicator (main chart)
# Original concept/source: ChartPrime open-source Pine Script, MPL-2.0.
# This is an independent platform port and preserves attribution.
#
# Important platform constraints:
# - all plot_* calls must remain at module/global scope
# - one indicator may use at most 50 plot calls
# - plot names must be <= 25 characters
# - moomoo has no Pine line/box object lifecycle; drawings are recreated as
#   fixed series channels. Current Fib/OTE geometry follows the open Pine logic;
#   previous history is limited to the latest two completed Fib sets.
# - no Python loop constructs a 500-deep full-history Sequence graph
# - Pine's live numeric label strings cannot be reproduced: moomoo plot_text()
#   accepts only one fixed scalar str while Sequence data is unavailable during
#   graph construction. Exact live values remain in the plot tooltip/legend and
#   output_parameter values.

import math
from ftool import *

indicator(
    "OTE_CP",
    "ChartPrime OTE Engine",
    True,
    "Source-aligned ChartPrime OTE geometry with memory-safe confirmed pivots, HH/LL shifts, dynamic anchors, swing labels, yellow OTE zone and optional previous sets.",
)

# -----------------------------------------------------------------------------
# Source-mapped settings
# -----------------------------------------------------------------------------
pivot_len = input_parameter("Pivot Length", 10)
show_swing_labels = input_parameter("Show Swing Markers", True)
show_structure_shifts = input_parameter("Show HH/LL Shift Lines", True)
show_ote = input_parameter("Show OTE Zone", True)
show_fib_lines = input_parameter("Show Fib Levels", True)
show_swing_diagonal = input_parameter("Show Swing Diagonal", True)
extend_fibs = input_parameter("Extend Fib Lines", True)
show_previous_fibs = input_parameter("Show Previous Fibs", False)

ote_upper = input_parameter("OTE Upper Level", 0.786)
ote_lower = input_parameter("OTE Lower Level", 0.618)

# 0=Solid, 1=Dashed, 2=Dotted. Current/previous Fib channels each contain
# one continuous segment, so native plot() styles can be used without bridge
# artifacts. HH/LL shift lines share history and therefore use segment masks.
fib_style = input_parameter("Fib Style 0Solid1Dash2Dot", 1)
diag_style = input_parameter("Diag Style 0Solid1Dash2Dot", 2)
shift_style = input_parameter("BOS Style 0Solid1Dash2Dot", 0)
label_size = input_parameter("Fib Label Size 1-3", 1)
hhll_label_size = input_parameter("HH LL Text Size 1-3", 1)
hhll_badge_size = input_parameter("HH LL Badge Size 1-5", 3)
swing_marker_size = input_parameter("Swing Marker Size 1-3", 1)
show_swing_marker_text = input_parameter("Show SH/SL Text", True)
label_gap_atr = input_parameter("HH LL Label Gap ATR", 0.22)

# TradingView uses a bool Show Previous Fibs and can retain many objects. The
# moomoo 50-channel ceiling permits the latest two completed sets.
previous_fib_sets = 2 if show_previous_fibs else 0

# -----------------------------------------------------------------------------
# Constants and colors (ChartPrime defaults)
# -----------------------------------------------------------------------------
_BIG = 1000000000.0
_SCAN_MAX = 500
_FIB_LEVELS = (0.000, 0.236, 0.382, 0.500, 0.618, 0.786, 1.000)

# ChartPrime-like structure colors. The OTE zone intentionally uses the user's
# requested pale yellow rather than the original direction-specific teal/red.
bull_line = Color.rgb(34, 197, 94, 178)
bear_line = Color.rgb(249, 115, 22, 178)
bull_badge = Color.rgb(34, 197, 94, 220)
bear_badge = Color.rgb(249, 115, 22, 220)
bull_text = Color.hex("#16A34A")
bear_text = Color.hex("#EA580C")
ote_zone_fill = Color.rgb(255, 226, 120, 58)  # pale yellow, ~23% opacity
ote_label_color = Color.rgb(180, 125, 0, 235)  # dark amber label text
fib_line_color = Color.rgb(211, 211, 211, 204)
fib_text_color = Color.hex("#5D606B")
swing_high_color = Color.rgb(249, 115, 22, 175)
swing_low_color = Color.rgb(34, 197, 94, 175)

# -----------------------------------------------------------------------------
# Base series and helpers
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
bar_no = bars_count(c)


def _age(cond):
    return replace_na(bars_last(cond), _BIG)


def _previous_age(cond):
    return replace_na(ref(bars_last(cond), 1), _BIG)


def _broadcast_last(x):
    return fill_na(iff(is_last, x, math.nan), "backward")


def _broadcast_last_bool(cond):
    return _broadcast_last(iff(cond, 1.0, 0.0)) > 0.5




def _style_mask(style_value):
    if style_value == 0:
        return _true
    if style_value == 2:
        return (bar_no % 3.0) == 0.0
    return (bar_no % 4.0) < 2.0


def _line_style(style_value):
    if style_value == 0:
        return Line.line
    if style_value == 1:
        return Line.line_dashed
    return Line.line_dotted


def _fib_price(level, anchor_high, anchor_low, bull_direction):
    price_range = anchor_high - anchor_low
    bull_price = anchor_high - price_range * level
    bear_price = anchor_low + price_range * level
    return iff(bull_direction, bull_price, bear_price)


def _current_confirmed_pivot_since(shift_event, pivot_event, pivot_value, find_maximum):
    """Most extreme confirmed pivot in the latest active shift.

    The former implementation created 501 nested ref/iff Sequence layers per
    direction.  This version broadcasts the latest shift age, masks only that
    current interval, and uses one native bounded HHV/LLV.  Equal extremes use
    the latest confirmed pivot, which is also the live anchor ChartPrime would
    retain after updating its mutable object.
    """
    shift_age = _broadcast_last(_age(shift_event))
    has_shift = shift_age < _BIG
    in_shift = has_shift & (x_age <= shift_age) & pivot_event
    if find_maximum:
        masked = iff(in_shift, pivot_value, 0.0 - _BIG)
        extreme = _broadcast_last(masked.hhv(_SCAN_MAX + 1))
    else:
        masked = iff(in_shift, pivot_value, _BIG)
        extreme = _broadcast_last(masked.llv(_SCAN_MAX + 1))
    selected = in_shift & (pivot_value == extreme)
    confirm_offset = _broadcast_last(_age(selected))
    valid = has_shift & (~is_na(extreme)) & (abs(extreme) < _BIG * 0.5)
    return iff(valid, extreme, math.nan), iff(valid, confirm_offset, math.nan)


def _diagonal(start_age, end_age, start_price, end_price, valid):
    span = max(start_age - end_age, 1.0)
    progress = start_age - x_age
    visible = valid & (x_age <= start_age) & (x_age >= end_age)
    value = start_price + (end_price - start_price) * progress / span
    return iff(visible, value, math.nan), visible


def _shift_segment(event, pivot_event, pivot_value, offset):
    """ChartPrime HH/LL horizontal segment: previous pivot bar -> shift confirmation bar."""
    next_event = bars_next(event)
    span_at_event = _previous_age(pivot_event) + 1.0 + offset
    span = fill_na(iff(event, span_at_event, math.nan), "backward")
    level = fill_na(iff(event, pivot_value, math.nan), "backward")
    visible = (~is_na(next_event)) & (~is_na(span)) & (next_event <= span)
    return iff(visible, level, math.nan)


def _freeze_previous(slot_event, old_high, old_low, old_bull, old_start_span, old_end_span):
    event_age = _broadcast_last(_age(slot_event))
    high_value = _broadcast_last(value_when(slot_event, old_high))
    low_value = _broadcast_last(value_when(slot_event, old_low))
    bull_value = _broadcast_last(value_when(slot_event, iff(old_bull, 1.0, 0.0))) > 0.5
    start_span = _broadcast_last(value_when(slot_event, old_start_span))
    end_span = _broadcast_last(value_when(slot_event, old_end_span))
    start_age = event_age + start_span
    end_age = event_age + end_span
    valid = (event_age < _BIG) & (~is_na(high_value)) & (~is_na(low_value)) & (high_value > low_value)
    horizontal_visible = valid & (x_age >= event_age) & (x_age <= start_age)
    return high_value, low_value, bull_value, start_age, end_age, event_age, valid, horizontal_visible


# -----------------------------------------------------------------------------
# Confirmed standard pivots: Pine ta.pivothigh/ta.pivotlow(length,length)
# The candidate is known only after pivot_len bars.  Equality against the full
# 2*length+1 window is the closest available series equivalent of ta.pivot*.
# -----------------------------------------------------------------------------
window = pivot_len * 2 + 1
enough_history = bars_count(c) > window
pvt_hi_raw = enough_history & (ref(h, pivot_len) == h.hhv(window))
pvt_lo_raw = enough_history & (ref(l, pivot_len) == l.llv(window))
pvt_hi_confirm = pvt_hi_raw
pvt_lo_confirm = pvt_lo_raw
pvt_hi_value = ref(h, pivot_len)
pvt_lo_value = ref(l, pivot_len)
pvt_hi_anchor = filter(backset(pvt_hi_confirm, pivot_len + 1), pivot_len)
pvt_lo_anchor = filter(backset(pvt_lo_confirm, pivot_len + 1), pivot_len)

last_swing_high = value_when(pvt_hi_confirm, pvt_hi_value)
last_swing_low = value_when(pvt_lo_confirm, pvt_lo_value)
previous_swing_high = ref(last_swing_high, 1)
previous_swing_low = ref(last_swing_low, 1)

higher_high_candidate = pvt_hi_confirm & (~is_na(previous_swing_high)) & (pvt_hi_value > previous_swing_high)
lower_low_candidate = pvt_lo_confirm & (~is_na(previous_swing_low)) & (pvt_lo_value < previous_swing_low)
raw_candidate = higher_high_candidate | lower_low_candidate
raw_direction = iff(lower_low_candidate, -1.0, iff(higher_high_candidate, 1.0, math.nan))
previous_direction = replace_na(ref(value_when(raw_candidate, raw_direction), 1), 0.0)

# Pine evaluates the bullish branch before the bearish branch.  When a bar
# confirms both a HH and LL, both shift flags are true and the bearish branch
# becomes the final trend state; retaining both flags is required for exact
# structure-line/alert parity.
bull_shift = higher_high_candidate & (previous_direction <= 0.0)
direction_after_bull = iff(bull_shift, 1.0, previous_direction)
bear_shift = lower_low_candidate & (direction_after_bull >= 0.0)
shift_event = bull_shift | bear_shift
shift_direction = iff(bear_shift, -1.0, 1.0)
trend_direction = replace_na(value_when(shift_event, shift_direction), 0.0)
trend_bull = trend_direction == 1.0
trend_bear = trend_direction == -1.0

# Fixed opposite anchor captured at the shift.
bull_anchor_low = value_when(bull_shift, last_swing_low)
bull_low_span_at_shift = value_when(bull_shift, _age(pvt_lo_confirm) + pivot_len)
bull_start_age = _age(bull_shift) + bull_low_span_at_shift

bear_anchor_high = value_when(bear_shift, last_swing_high)
bear_high_span_at_shift = value_when(bear_shift, _age(pvt_hi_confirm) + pivot_len)
bear_start_age = _age(bear_shift) + bear_high_span_at_shift

# Dynamic trend-side anchor stretches only when a newly confirmed extreme pivot
# extends the active direction.
bull_anchor_high, bull_high_confirm_age = _current_confirmed_pivot_since(
    bull_shift, pvt_hi_confirm, pvt_hi_value, True
)
bear_anchor_low, bear_low_confirm_age = _current_confirmed_pivot_since(
    bear_shift, pvt_lo_confirm, pvt_lo_value, False
)
bull_end_age = bull_high_confirm_age + pivot_len
bear_end_age = bear_low_confirm_age + pivot_len

fib_anchor_high = iff(trend_bull, bull_anchor_high, bear_anchor_high)
fib_anchor_low = iff(trend_bull, bull_anchor_low, bear_anchor_low)
active_start_age = iff(trend_bull, bull_start_age, bear_start_age)
active_end_age = iff(trend_bull, bull_end_age, bear_end_age)
active_shift_age = iff(trend_bull, _age(bull_shift), _age(bear_shift))
active_valid = (trend_bull | trend_bear) & (~is_na(fib_anchor_high)) & (~is_na(fib_anchor_low)) & (fib_anchor_high > fib_anchor_low)

# Freeze the latest active state across the chart so the current Fib grid is a
# single coherent object, like Pine's mutable line/box objects.
cur_high = _broadcast_last(fib_anchor_high)
cur_low = _broadcast_last(fib_anchor_low)
cur_bull = _broadcast_last_bool(trend_bull)
cur_start_age = _broadcast_last(active_start_age)
cur_end_age = _broadcast_last(active_end_age)
cur_shift_age = _broadcast_last(active_shift_age)
cur_valid = _broadcast_last_bool(active_valid)

if extend_fibs:
    current_horizontal_visible = cur_valid & (x_age <= cur_start_age)
else:
    current_horizontal_visible = cur_valid & (x_age <= cur_start_age) & (x_age >= cur_shift_age)
current_ote_visible = cur_valid & (x_age <= cur_start_age)

current_fib = []
for level in _FIB_LEVELS:
    current_fib.append(_fib_price(level, cur_high, cur_low, cur_bull))

ote_price_1 = _fib_price(ote_upper, cur_high, cur_low, cur_bull)
ote_price_2 = _fib_price(ote_lower, cur_high, cur_low, cur_bull)
ote_top = max(ote_price_1, ote_price_2)
ote_bottom = min(ote_price_1, ote_price_2)
ote_mid = (ote_top + ote_bottom) / 2.0
current_direction_color = iff(cur_bull, bull_line, bear_line)
current_ote_color = ote_zone_fill

cur_start_price = iff(cur_bull, cur_low, cur_high)
cur_end_price = iff(cur_bull, cur_high, cur_low)
current_diag_value, current_diag_visible = _diagonal(
    cur_start_age, cur_end_age, cur_start_price, cur_end_price, cur_valid
)

# -----------------------------------------------------------------------------
# Up to two prior completed Fib sets. The entire historical-object graph is
# skipped when the Pine-default Show Previous Fibs setting is off.
# -----------------------------------------------------------------------------
if show_previous_fibs:
    old_high_at_finalize = ref(fib_anchor_high, 1)
    old_low_at_finalize = ref(fib_anchor_low, 1)
    old_bull_at_finalize = ref(trend_bull, 1)
    old_start_span_at_finalize = ref(active_start_age, 1) + 1.0
    old_end_span_at_finalize = ref(active_end_age, 1) + 1.0
    finalize_event = shift_event & (~is_na(old_high_at_finalize)) & (~is_na(old_low_at_finalize)) & (old_high_at_finalize > old_low_at_finalize)
    finalize_count = iff(finalize_event, 1.0, 0.0).sum(0)
    slot_0_event = finalize_event & (((finalize_count - 1.0) % 2.0) == 0.0)
    slot_1_event = finalize_event & (((finalize_count - 1.0) % 2.0) == 1.0)

    prev0 = _freeze_previous(slot_0_event, old_high_at_finalize, old_low_at_finalize, old_bull_at_finalize, old_start_span_at_finalize, old_end_span_at_finalize)
    prev1 = _freeze_previous(slot_1_event, old_high_at_finalize, old_low_at_finalize, old_bull_at_finalize, old_start_span_at_finalize, old_end_span_at_finalize)
    prev0_visible = prev0[7]
    prev1_visible = prev1[7]
    prev0_diag_valid = prev0[6]
    prev1_diag_valid = prev1[6]

    prev0_fib = []
    prev1_fib = []
    for level in _FIB_LEVELS:
        prev0_fib.append(_fib_price(level, prev0[0], prev0[1], prev0[2]))
        prev1_fib.append(_fib_price(level, prev1[0], prev1[1], prev1[2]))

    prev0_ote_a = _fib_price(ote_upper, prev0[0], prev0[1], prev0[2])
    prev0_ote_b = _fib_price(ote_lower, prev0[0], prev0[1], prev0[2])
    prev0_ote_top = max(prev0_ote_a, prev0_ote_b)
    prev0_ote_bottom = min(prev0_ote_a, prev0_ote_b)
    prev0_start_price = iff(prev0[2], prev0[1], prev0[0])
    prev0_end_price = iff(prev0[2], prev0[0], prev0[1])
    prev0_diag, prev0_diag_visible = _diagonal(prev0[3], prev0[4], prev0_start_price, prev0_end_price, prev0_diag_valid)

    prev1_ote_a = _fib_price(ote_upper, prev1[0], prev1[1], prev1[2])
    prev1_ote_b = _fib_price(ote_lower, prev1[0], prev1[1], prev1[2])
    prev1_ote_top = max(prev1_ote_a, prev1_ote_b)
    prev1_ote_bottom = min(prev1_ote_a, prev1_ote_b)
    prev1_start_price = iff(prev1[2], prev1[1], prev1[0])
    prev1_end_price = iff(prev1[2], prev1[0], prev1[1])
    prev1_diag, prev1_diag_visible = _diagonal(prev1[3], prev1[4], prev1_start_price, prev1_end_price, prev1_diag_valid)
else:
    prev0 = (_nan, _nan, _false, _nan, _nan, _nan, _false, _false)
    prev1 = (_nan, _nan, _false, _nan, _nan, _nan, _false, _false)
    prev0_visible = _false
    prev1_visible = _false
    prev0_diag_visible = _false
    prev1_diag_visible = _false
    prev0_fib = [_nan, _nan, _nan, _nan, _nan, _nan, _nan]
    prev1_fib = [_nan, _nan, _nan, _nan, _nan, _nan, _nan]
    prev0_ote_top = _nan
    prev0_ote_bottom = _nan
    prev1_ote_top = _nan
    prev1_ote_bottom = _nan
    prev0_diag = _nan
    prev1_diag = _nan

prev0_ote_color = ote_zone_fill
prev1_ote_color = ote_zone_fill

# -----------------------------------------------------------------------------
# Structure-shift and swing-label geometry
# -----------------------------------------------------------------------------
bull_shift_line = _shift_segment(bull_shift, pvt_hi_confirm, pvt_hi_value, pivot_len)
bear_shift_line = _shift_segment(bear_shift, pvt_lo_confirm, pvt_lo_value, pivot_len)
# ChartPrime places the HH/LL badge on the later shift-confirmation bar, while
# the new extreme itself remains the badge's y value. Ordinary confirmed swing
# markers stay on their true pivot bars.
bull_shift_anchor = bull_shift
bear_shift_anchor = bear_shift

true_range = max(h, ref(c, 1)) - min(l, ref(c, 1))
atr100 = true_range.smma(100, 1)
line_half = max(atr100 * 0.0025, c * 0.000012)
label_gap = max(atr100 * label_gap_atr, c * 0.0012)

fib_line_style = _line_style(fib_style)
shift_mask = _style_mask(shift_style)
diag_line_style = _line_style(diag_style)

if show_fib_lines:
    show_current_fib = current_horizontal_visible
    show_prev0_lines = prev0_visible
    show_prev1_lines = prev1_visible
    current_fib_label_cond = is_last & cur_valid
else:
    show_current_fib = _false
    show_prev0_lines = _false
    show_prev1_lines = _false
    current_fib_label_cond = _false

if show_swing_diagonal:
    show_current_diag = current_diag_visible
    show_prev0_diag = prev0_diag_visible
    show_prev1_diag = prev1_diag_visible
else:
    show_current_diag = _false
    show_prev0_diag = _false
    show_prev1_diag = _false

if show_ote:
    show_current_ote = current_ote_visible
    show_prev0_ote = prev0_visible
    show_prev1_ote = prev1_visible
    current_ote_label_cond = is_last & cur_valid
else:
    show_current_ote = _false
    show_prev0_ote = _false
    show_prev1_ote = _false
    current_ote_label_cond = _false

if show_structure_shifts:
    bull_shift_draw = (~is_na(bull_shift_line)) & shift_mask
    bear_shift_draw = (~is_na(bear_shift_line)) & shift_mask
    bull_shift_label = bull_shift_anchor
    bear_shift_label = bear_shift_anchor
else:
    bull_shift_draw = _false
    bear_shift_draw = _false
    bull_shift_label = _false
    bear_shift_label = _false

if show_swing_labels:
    swing_high_marker = pvt_hi_anchor
    swing_low_marker = pvt_lo_anchor
else:
    swing_high_marker = _false
    swing_low_marker = _false

# Label backgrounds use native label icons; white fixed text is drawn over them.
# This is the closest moomoo equivalent of Pine label.style_label_down/up.
hh_icon_y = pvt_hi_value
ll_icon_y = pvt_lo_value
hh_text_y = pvt_hi_value + label_gap * 0.52
ll_text_y = pvt_lo_value - label_gap * 0.52
swing_text_gap = max(atr100 * 0.12, c * 0.0008)
sh_text_y = h + swing_text_gap
sl_text_y = l - swing_text_gap
if show_swing_marker_text and show_swing_labels:
    swing_high_text = pvt_hi_anchor
    swing_low_text = pvt_lo_anchor
else:
    swing_high_text = _false
    swing_low_text = _false

# Right-edge Fibonacci labels. moomoo plot_text requires a fixed scalar string.
# Live level prices remain visible in the indicator legend and output parameters.
fib_text_000 = "0.000"
fib_text_236 = "0.236"
fib_text_382 = "0.382"
fib_text_500 = "0.500"
fib_text_618 = "0.618"
fib_text_786 = "0.786"
fib_text_100 = "1.000"

# -----------------------------------------------------------------------------
# GLOBAL PLOTS — 45/50
# -----------------------------------------------------------------------------
# Current Fibonacci levels (7). Native plot lines are smooth and map directly
# to Pine line.new() because this channel contains only the current Fib set.
plot("Fib 0.000", iff(show_current_fib, current_fib[0], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("Fib 0.236", iff(show_current_fib, current_fib[1], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("Fib 0.382", iff(show_current_fib, current_fib[2], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("Fib 0.500", iff(show_current_fib, current_fib[3], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("Fib 0.618", iff(show_current_fib, current_fib[4], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("Fib 0.786", iff(show_current_fib, current_fib[5], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("Fib 1.000", iff(show_current_fib, current_fib[6], math.nan), fib_line_color, fib_line_style, 1, 0)

# Current level labels at the latest bar (7). The text is intentionally static;
# live prices are exposed by the plotted series and output_parameter values.
plot_text("0.000", current_fib_label_cond, current_fib[0], fib_text_000, fib_text_color, label_size, 0, 0, 0)
plot_text("0.236", current_fib_label_cond, current_fib[1], fib_text_236, fib_text_color, label_size, 0, 0, 0)
plot_text("0.382", current_fib_label_cond, current_fib[2], fib_text_382, fib_text_color, label_size, 0, 0, 0)
plot_text("0.500", current_fib_label_cond, current_fib[3], fib_text_500, fib_text_color, label_size, 0, 0, 0)
plot_text("0.618", current_fib_label_cond, current_fib[4], fib_text_618, fib_text_color, label_size, 0, 0, 0)
plot_text("0.786", current_fib_label_cond, current_fib[5], fib_text_786, fib_text_color, label_size, 0, 0, 0)
plot_text("1.000", current_fib_label_cond, current_fib[6], fib_text_100, fib_text_color, label_size, 0, 0, 0)

# Current OTE and diagonal (3)
plot_fillcolor("OTE Zone", ote_top, ote_bottom, show_current_ote, current_ote_color, 0)
plot_text("OTE Label", current_ote_label_cond, ote_mid, "OTE", ote_label_color, label_size, 0, 0, 0)
plot("Swing Diagonal", iff(show_current_diag, current_diag_value, math.nan), current_direction_color, diag_line_style, 1, 0)

# HH/LL direction shifts and swing markers (8). Shift lines span the prior
# same-side pivot to the confirmation bar, exactly like the Pine BOS geometry.
plot_stickline("HH Shift Line", bull_shift_draw, bull_shift_line - line_half, bull_shift_line + line_half, 0.90, False, False, bull_line, 0)
plot_stickline("LL Shift Line", bear_shift_draw, bear_shift_line - line_half, bear_shift_line + line_half, 0.90, False, False, bear_line, 0)
plot_icon("HH Badge", bull_shift_label, hh_icon_y, Shape.labeldown, bull_badge, hhll_badge_size, 0, 0, 0)
plot_icon("LL Badge", bear_shift_label, ll_icon_y, Shape.labelup, bear_badge, hhll_badge_size, 0, 0, 0)
plot_text("HH Text", bull_shift_label, hh_text_y, "HH ▲", Color.white, hhll_label_size, 0, 0, 0)
plot_text("LL Text", bear_shift_label, ll_text_y, "LL ▼", Color.white, hhll_label_size, 0, 0, 0)
plot_icon("Swing High", swing_high_marker, h, Shape.triangledown, swing_high_color, swing_marker_size, 0, 0, 0)
plot_icon("Swing Low", swing_low_marker, l, Shape.triangleup, swing_low_color, swing_marker_size, 0, 0, 0)
plot_text("Swing High Text", swing_high_text, sh_text_y, "SH", bear_text, swing_marker_size, 0, 0, 0)
plot_text("Swing Low Text", swing_low_text, sl_text_y, "SL", bull_text, swing_marker_size, 0, 0, 0)

# Previous completed Fib set 0 (9)
plot("P0 Fib 0.000", iff(show_prev0_lines, prev0_fib[0], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("P0 Fib 0.236", iff(show_prev0_lines, prev0_fib[1], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("P0 Fib 0.382", iff(show_prev0_lines, prev0_fib[2], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("P0 Fib 0.500", iff(show_prev0_lines, prev0_fib[3], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("P0 Fib 0.618", iff(show_prev0_lines, prev0_fib[4], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("P0 Fib 0.786", iff(show_prev0_lines, prev0_fib[5], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("P0 Fib 1.000", iff(show_prev0_lines, prev0_fib[6], math.nan), fib_line_color, fib_line_style, 1, 0)
plot_fillcolor("P0 OTE", prev0_ote_top, prev0_ote_bottom, show_prev0_ote, prev0_ote_color, 0)
plot("P0 Diagonal", iff(show_prev0_diag, prev0_diag, math.nan), iff(prev0[2], bull_line, bear_line), diag_line_style, 1, 0)

# Previous completed Fib set 1 (9)
plot("P1 Fib 0.000", iff(show_prev1_lines, prev1_fib[0], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("P1 Fib 0.236", iff(show_prev1_lines, prev1_fib[1], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("P1 Fib 0.382", iff(show_prev1_lines, prev1_fib[2], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("P1 Fib 0.500", iff(show_prev1_lines, prev1_fib[3], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("P1 Fib 0.618", iff(show_prev1_lines, prev1_fib[4], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("P1 Fib 0.786", iff(show_prev1_lines, prev1_fib[5], math.nan), fib_line_color, fib_line_style, 1, 0)
plot("P1 Fib 1.000", iff(show_prev1_lines, prev1_fib[6], math.nan), fib_line_color, fib_line_style, 1, 0)
plot_fillcolor("P1 OTE", prev1_ote_top, prev1_ote_bottom, show_prev1_ote, prev1_ote_color, 0)
plot("P1 Diagonal", iff(show_prev1_diag, prev1_diag, math.nan), iff(prev1[2], bull_line, bear_line), diag_line_style, 1, 0)

in_ote = cur_valid & (c <= ote_top) & (c >= ote_bottom)
output_parameter(
    bullish_shift=bull_shift,
    bearish_shift=bear_shift,
    trend_bullish=trend_bull,
    trend_bearish=trend_bear,
    price_in_ote=in_ote,
    fib_000=current_fib[0],
    fib_236=current_fib[1],
    fib_382=current_fib[2],
    fib_500=current_fib[3],
    fib_618=current_fib[4],
    fib_786=current_fib[5],
    fib_1000=current_fib[6],
    ote_top=ote_top,
    ote_bottom=ote_bottom,
    anchor_high=cur_high,
    anchor_low=cur_low,
    confirmed_swing_high=iff(pvt_hi_confirm, pvt_hi_value, math.nan),
    confirmed_swing_low=iff(pvt_lo_confirm, pvt_lo_value, math.nan),
)
