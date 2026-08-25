# Smart Money Fibonacci OTE — standalone moomoo Python indicator v1.0
#
# Independent implementation informed by the published behavior of ChartPrime's
# open-source Smart Money Fibonacci OTE Engine.  No third-party Pine source code
# is included or copied.  The script is a dynamic retracement-location tool and
# does not emit buy/sell instructions.
#
# Client-confirmed moomoo constraints:
# - all plot_* calls at module/global scope
# - <= 50 static plot calls per indicator
# - plot name <= 25 characters
# - plot_stickline has 9 positional arguments

import math
from ftool import *

indicator(
    "OTE",
    "Smart Money Fib OTE",
    True,
    "HH/LL direction-shift Fibonacci grid with a dynamic 61.8%-78.6% OTE zone. Location tool only.",
)

pivot_length = input_parameter("Pivot Length", 5)
fib_shallow = input_parameter("OTE Shallow Fib", 0.618)
fib_optimal = input_parameter("OTE Optimal Fib", 0.705)
fib_deep = input_parameter("OTE Deep Fib", 0.786)
show_zone = input_parameter("Show OTE Zone", True)
show_ote_levels = input_parameter("Show OTE Levels", True)
show_full_grid = input_parameter("Show Full Fib Grid", True)
show_labels = input_parameter("Show OTE Labels", True)
invalidate_origin = input_parameter("Invalidate Origin Break", True)
monochrome = input_parameter("Style: Monochrome", False)

if monochrome:
    bull = Color.hex("#B2B5BE")
    bear = Color.hex("#5D606B")
    bull_fill = Color.rgb(178, 181, 190, 64)
    bear_fill = Color.rgb(93, 96, 107, 64)
else:
    bull = Color.hex("#089981")
    bear = Color.hex("#F23645")
    bull_fill = Color.rgb(8, 153, 129, 58)
    bear_fill = Color.rgb(242, 54, 69, 58)
neutral = Color.hex("#878B94")

h = high()
l = low()
c = close()

_BIG = 1000000000.0
_SCAN_MAX = 500
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
    """Confirmed alternating pivots using the suite's source-aligned engine."""
    high_candidate = ref(h, length) > h.hhv(length)
    low_candidate = (ref(l, length) < l.llv(length)) & (~high_candidate)
    prev_high_age = replace_na(ref(bars_last(high_candidate), 1), _BIG)
    prev_low_age = replace_na(ref(bars_last(low_candidate), 1), _BIG)
    previous_leg_is_bearish = prev_high_age <= prev_low_age
    top_confirm = high_candidate & (~previous_leg_is_bearish)
    bottom_confirm = low_candidate & previous_leg_is_bearish
    top_value = ref(h, length)
    bottom_value = ref(l, length)
    return top_confirm, bottom_confirm, top_value, bottom_value


def _scan_since(event, source, find_maximum):
    """Current extreme from the latest direction shift, capped at 500 bars."""
    start_age = _age(event)
    has_start = start_age < _BIG
    best = _nan
    for k in range(0, _SCAN_MAX + 1):
        candidate = ref(source, k)
        eligible = has_start & (start_age >= k)
        if find_maximum:
            better = eligible & (is_na(best) | (candidate > best))
        else:
            better = eligible & (is_na(best) | (candidate < best))
        best = iff(better, candidate, best)
    return best


# Pivot-and-shift direction engine.  A Higher High can establish bullish
# direction; a Lower Low can establish bearish direction.  Repeated HH/LL in
# the same direction stretch the current grid rather than starting a new one.
top_confirm, bottom_confirm, top_value, bottom_value = _swing_state(pivot_length)
previous_top = ref(value_when(top_confirm, top_value), 1)
previous_bottom = ref(value_when(bottom_confirm, bottom_value), 1)
latest_top = value_when(top_confirm, top_value)
latest_bottom = value_when(bottom_confirm, bottom_value)

higher_high = top_confirm & (~is_na(previous_top)) & (top_value > previous_top)
lower_low = bottom_confirm & (~is_na(previous_bottom)) & (bottom_value < previous_bottom)
raw_shift = higher_high | lower_low
raw_direction = iff(higher_high, 1.0, -1.0)
direction_before = replace_na(ref(value_when(raw_shift, raw_direction), 1), 0.0)
bull_shift = higher_high & (direction_before != 1.0) & (~is_na(latest_bottom))
bear_shift = lower_low & (direction_before != -1.0) & (~is_na(latest_top))
shift_event = bull_shift | bear_shift
shift_direction = iff(bull_shift, 1.0, -1.0)
origin_at_shift = iff(bull_shift, latest_bottom, latest_top)

# Freeze the latest structural shift.  The expansion endpoint remains dynamic:
# bullish grids stretch with new highs and bearish grids with new lows.
shift_age = _broadcast_last(_age(shift_event))
direction = _broadcast_last(value_when(shift_event, shift_direction))
origin = _broadcast_last(value_when(shift_event, origin_at_shift))
stretch_high = _broadcast_last(_scan_since(shift_event, h, True))
stretch_low = _broadcast_last(_scan_since(shift_event, l, False))
impulse_high = iff(direction > 0, stretch_high, origin)
impulse_low = iff(direction > 0, origin, stretch_low)
range_size = impulse_high - impulse_low
has_grid = (shift_age < _BIG) & (~is_na(direction)) & (~is_na(origin)) & (range_size > 0)
grid_span = has_grid & (x_age <= shift_age)

# Optional structural invalidation.  Because pivots confirm with delay, this
# explicit origin boundary prevents a broken old grid remaining actionable.
after_shift = grid_span & (x_age < shift_age)
origin_break = after_shift & (((direction > 0) & (l < origin)) | ((direction < 0) & (h > origin)))
if invalidate_origin:
    invalidated = _broadcast_last_bool(_age(origin_break) < shift_age)
else:
    invalidated = _false
active = grid_span & (~invalidated)


def _fib(level):
    return iff(direction > 0, impulse_high - level * range_size, impulse_low + level * range_size)


fib_000 = _fib(0.000)
fib_236 = _fib(0.236)
fib_382 = _fib(0.382)
fib_500 = _fib(0.500)
fib_618 = _fib(fib_shallow)
fib_705 = _fib(fib_optimal)
fib_786 = _fib(fib_deep)
fib_100 = _fib(1.000)
zone_top = max(fib_618, fib_786)
zone_bottom = min(fib_618, fib_786)

zone_visible = active if show_zone else _false
ote_visible = active if show_ote_levels else _false
grid_visible = active if show_full_grid else _false
direction_color = iff(direction > 0, bull, bear)
zone_color = iff(direction > 0, bull_fill, bear_fill)

true_range = max(h, ref(c, 1)) - min(l, ref(c, 1))
atr200 = true_range.smma(200, 1)
line_half = max(atr200 * 0.004, c * 0.00002)
label_gap = max(atr200 * 0.16, c * 0.0015)
if show_labels:
    bull_label = is_last & zone_visible & (direction > 0)
    bear_label = is_last & zone_visible & (direction < 0)
else:
    bull_label = _false
    bear_label = _false

contact = active & (l <= zone_top) & (h >= zone_bottom)
entered = contact & (~ref(contact, 1))

# GLOBAL PLOTS — 11/50
plot_fillcolor("OTE zone", zone_top, zone_bottom, zone_visible, zone_color, 0)
plot_stickline("Fib 0.000", grid_visible, fib_000 - line_half, fib_000 + line_half, 0.95, False, False, direction_color, 0)
plot_stickline("Fib 0.236", grid_visible, fib_236 - line_half, fib_236 + line_half, 0.40, False, True, neutral, 0)
plot_stickline("Fib 0.382", grid_visible, fib_382 - line_half, fib_382 + line_half, 0.40, False, True, neutral, 0)
plot_stickline("Fib 0.500", grid_visible, fib_500 - line_half, fib_500 + line_half, 0.40, False, True, neutral, 0)
plot_stickline("Fib 0.618", ote_visible, fib_618 - line_half, fib_618 + line_half, 0.95, False, False, direction_color, 0)
plot_stickline("Fib 0.705", ote_visible, fib_705 - line_half, fib_705 + line_half, 0.45, False, True, direction_color, 0)
plot_stickline("Fib 0.786", ote_visible, fib_786 - line_half, fib_786 + line_half, 0.95, False, False, direction_color, 0)
plot_stickline("Fib 1.000", grid_visible, fib_100 - line_half, fib_100 + line_half, 0.95, False, False, direction_color, 0)
plot_text("Bull OTE tag", bull_label, zone_bottom - label_gap, "Bull OTE", bull, 1, 0, 0, 0)
plot_text("Bear OTE tag", bear_label, zone_top + label_gap, "Bear OTE", bear, 1, 0, 0, 0)

output_parameter(
    bullish_direction_shift=bull_shift,
    bearish_direction_shift=bear_shift,
    ote_zone_entered=entered,
    ote_origin_invalidated=origin_break,
)
