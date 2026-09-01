# Historical Similarity Projection for moomoo Python custom indicators
# v2.0.1 — exhaustive all-bar search; fmath-compatible logarithms
#
# Unlike v1.x, this edition does NOT sample 48 fixed offsets. It computes one
# normalized-shape distance value at every eligible historical anchor bar, then
# uses native LLV/LLV_BARS primitives to select the best analogue across the
# requested history horizon. With Search History Bars=2520 on a daily chart,
# every eligible daily anchor in roughly ten trading years is evaluated.
#
# Client-safe design:
# - all plot_* calls remain at module/global scope
# - <= 50 static plot calls
# - no thousands-deep ref/iff candidate graph
# - scan depth is handled by native llv()/llv_bars(), not one candidate graph
#   per historical offset
# - dynamic source dates are rendered with fixed digit plot_text channels

import math
from fdatetime import *
from fmath import *
from ftool import *

indicator(
    "HIST_SIM",
    "Historical Similarity 10Y",
    True,
    "Exhaustive normalized-path analogue search across up to 2520 daily bars, with an exact selected match and realized continuation projection.",
)

# ------------------------------- Inputs -----------------------------------
lookback_bars = input_parameter("Lookback Window", 50)
projection_bars = input_parameter("Projection Length", 20)
search_history_bars = input_parameter("Search History Bars", 2520)
recent_bars = input_parameter("Recent Emphasis Bars", 10)
recent_weight = input_parameter("Recent Weight", 1.0)
shock_weight = input_parameter("Last Bar Shock Weight", 2.0)
min_fit_score = input_parameter("Min Fit Score", 60.0)
similarity_mode = input_parameter("Similarity 0Pct1Log", 1)
show_match = input_parameter("Show Matched History", True)
show_projection = input_parameter("Show Projection", True)
show_match_boundaries = input_parameter("Show Match Boundaries", True)
show_source_date_on_match = input_parameter("Show Source Date On Match", True)
show_reference_window = input_parameter("Show Reference Window", False)
show_quality_label = input_parameter("Show Quality Label", True)
match_style_mode = input_parameter("Match 0Solid1Dash2Dot", 1)
projection_style_mode = input_parameter("Proj 0Solid1Dash2Dot", 0)
match_width = input_parameter("Match Width 1-3", 1)
projection_width = input_parameter("Projection Width 1-4", 3)

# Guard the amount of graph construction caused by the template itself. Search
# depth does not create one graph per bar; Lookback Window does create one
# comparison term per template point, so it is deliberately bounded.
if lookback_bars < 10:
    lookback_bars = 10
if lookback_bars > 120:
    lookback_bars = 120
if projection_bars < 5:
    projection_bars = 5
if projection_bars > 120:
    projection_bars = 120
if search_history_bars < 252:
    search_history_bars = 252
if search_history_bars > 5000:
    search_history_bars = 5000
if recent_bars < 2:
    recent_bars = 2
if recent_bars > lookback_bars:
    recent_bars = lookback_bars
if recent_weight < 0:
    recent_weight = 0.0
if shock_weight < 0:
    shock_weight = 0.0
if min_fit_score < 0:
    min_fit_score = 0.0
if min_fit_score > 100:
    min_fit_score = 100.0
if similarity_mode != 1:
    similarity_mode = 0

# ------------------------------- Colors -----------------------------------
analogue_color = Color.rgb(33, 87, 243, 230)
reference_fill = Color.rgb(135, 139, 148, 22)
strong_color = Color.rgb(8, 153, 129, 235)
moderate_color = Color.rgb(242, 153, 74, 235)
weak_color = Color.rgb(242, 54, 69, 235)
neutral_color = Color.rgb(93, 96, 107, 220)
warning_color = Color.rgb(242, 153, 74, 235)

if match_style_mode == 2:
    match_style = Line.line_dotted
elif match_style_mode == 1:
    match_style = Line.line_dashed
else:
    match_style = Line.line

if projection_style_mode == 2:
    projection_style = Line.line_dotted
elif projection_style_mode == 1:
    projection_style = Line.line_dashed
else:
    projection_style = Line.line

# ----------------------------- Core series --------------------------------
c = close()
h = high()
l = low()
x_age = curr_bars_count(c)
is_last = x_age == 0
_false = c != c
_nan = c * math.nan
_BIG = 1000000000000.0

reference_mask = x_age < lookback_bars
projection_base_mask = x_age <= projection_bars
# Prevent the source match and its realized continuation from overlapping the
# current reference window. This follows the v1.x exclusion principle, but the
# search now evaluates every anchor beyond this boundary.
minimum_anchor_age = lookback_bars + projection_bars + 1

true_range = max(h, ref(c, 1)) - min(l, ref(c, 1))
atr20 = true_range.smma(20, 1)
marker_gap = max(atr20 * 0.35, c * 0.003)


def _broadcast_last(x):
    """Broadcast the value observed on the current last bar backward."""
    return fill_na(iff(is_last, x, math.nan), "backward")


# ---------------------- Exact all-anchor distance -------------------------
# Current template points are frozen from the latest Lookback Window. At every
# historical bar, ref(c, j) represents point j of the candidate window ending
# at that bar. This constructs O(Lookback) graph terms and scores every anchor,
# rather than constructing O(number_of_candidate_offsets) separate windows.
current_start = _broadcast_last(ref(c, lookback_bars - 1))
historical_start = ref(c, lookback_bars - 1)
shape_sum = c * 0.0
recent_sum = c * 0.0

for j in range(0, lookback_bars):
    current_point = _broadcast_last(ref(c, j))
    historical_point = ref(c, j)
    if similarity_mode == 1:
        current_feature = math_log(current_point / current_start, 2.718281828459045) * 100.0
        historical_feature = math_log(historical_point / historical_start, 2.718281828459045) * 100.0
    else:
        current_feature = ((current_point / current_start) - 1.0) * 100.0
        historical_feature = ((historical_point / historical_start) - 1.0) * 100.0
    point_diff = current_feature - historical_feature
    point_error = point_diff * point_diff
    shape_sum = shape_sum + point_error
    if j < recent_bars:
        recent_sum = recent_sum + point_error

full_mse = shape_sum / (lookback_bars * 1.0)
tail_mse = recent_sum / (recent_bars * 1.0)

if similarity_mode == 1:
    current_last_return = _broadcast_last(math_log(c / ref(c, 1), 2.718281828459045) * 100.0)
    historical_last_return = math_log(c / ref(c, 1), 2.718281828459045) * 100.0
else:
    current_last_return = _broadcast_last(((c / ref(c, 1)) - 1.0) * 100.0)
    historical_last_return = ((c / ref(c, 1)) - 1.0) * 100.0

shock_gap = abs(current_last_return - historical_last_return)
shock_error = shock_gap * shock_gap
raw_distance = full_mse + recent_weight * tail_mse + shock_weight * shock_error

weight_total = 1.0 + recent_weight + shock_weight
full_similarity = 100.0 / (1.0 + full_mse / 25.0)
tail_similarity = 100.0 / (1.0 + tail_mse / 16.0)
shock_similarity = 100.0 / (1.0 + shock_error / 4.0)
fit_score_series = (full_similarity + recent_weight * tail_similarity + shock_weight * shock_similarity) / weight_total

# Candidate anchors must be old enough to contain both the complete match and
# the realized continuation, and their source window must have valid prices.
anchor_in_range = (x_age >= minimum_anchor_age) & (x_age <= search_history_bars)
source_valid = (~is_na(historical_start)) & (~is_na(c)) & (historical_start > 0) & (c > 0)
safe_distance = iff(anchor_in_range & source_valid, raw_distance, _BIG)

# Native rolling minimum performs the exhaustive search across all bars in the
# requested horizon. llv_bars returns the exact selected anchor age.
search_span = search_history_bars + 1
selected_distance = _broadcast_last(safe_distance.llv(search_span, 1))
selected_anchor_age = _broadcast_last(safe_distance.llv_bars(search_span, 1))
has_candidate = (selected_distance < _BIG * 0.5) & (selected_anchor_age >= minimum_anchor_age)
best_anchor_event = has_candidate & (abs(x_age - selected_anchor_age) < 0.5)
selected_fit = _broadcast_last(value_when(best_anchor_event, fit_score_series))
fit_pass = has_candidate & (selected_fit >= min_fit_score)

# --------------------- Reconstruct exact selected path --------------------
current_anchor = _broadcast_last(c)
source_anchor = _broadcast_last(value_when(best_anchor_event, c))
scale = current_anchor / source_anchor

# Match path: source anchor maps to the current last bar; source j-bars-before
# anchor maps to the current j-bars-before point. The selected source age is
# dynamic, but value_when() extracts each exact source point without a dynamic
# ref offset.
selected_match = c * math.nan
for j in range(0, lookback_bars):
    source_point = _broadcast_last(value_when(best_anchor_event, ref(c, j)))
    current_position = abs(x_age - (j * 1.0)) < 0.5
    selected_match = iff(current_position, source_point * scale, selected_match)

# Realized continuation: source k-bars-after anchor is captured where
# ref(best_anchor_event, k) becomes true. The base path is built on the latest
# Projection Length+1 existing bars and shifted right by plot(ref=P).
selected_projection = c * math.nan
for k in range(0, projection_bars + 1):
    if k == 0:
        source_future_point = source_anchor
    else:
        source_future_point = _broadcast_last(value_when(ref(best_anchor_event, k), c))
    base_age = projection_bars - k
    projection_position = abs(x_age - (base_age * 1.0)) < 0.5
    selected_projection = iff(projection_position, source_future_point * scale, selected_projection)

if show_match:
    match_draw = reference_mask & fit_pass
else:
    match_draw = _false
if show_projection:
    projection_draw = projection_base_mask & fit_pass
else:
    projection_draw = _false

match_start_price = _broadcast_last(ref(selected_match, lookback_bars - 1))
match_endpoint = current_anchor
projection_end = _broadcast_last(selected_projection)
projected_bullish = projection_end >= current_anchor
marker_gap_last = _broadcast_last(marker_gap)

# ------------------------- Source-date metadata ---------------------------
# year/month/day explicitly consume the price Sequence; this avoids the
# zero-argument client issue encountered in earlier modules.
ymd = year(c) * 10000.0 + month(c) * 100.0 + day(c)
source_start_ymd = _broadcast_last(value_when(best_anchor_event, ref(ymd, lookback_bars - 1)))
source_anchor_ymd = _broadcast_last(value_when(best_anchor_event, ymd))
source_end_ymd = _broadcast_last(value_when(ref(best_anchor_event, projection_bars), ymd))

if show_match_boundaries:
    match_start_label = fit_pass & (abs(x_age - (lookback_bars - 1.0)) < 0.5)
    match_join_label = fit_pass & is_last
else:
    match_start_label = _false
    match_join_label = _false
match_start_y = match_start_price + marker_gap_last * 2.35
match_join_y = match_endpoint + marker_gap_last * 2.35

# Render two dynamic YYYY-MM-DD values directly on the CURRENT dashed match:
# source start date at its left edge and source anchor date at its right edge.
def _date_digit(code, divisor):
    return floor(code / divisor) - floor(code / (divisor * 10.0)) * 10.0

src_start_d1 = _date_digit(source_start_ymd, 10000000.0)
src_start_d2 = _date_digit(source_start_ymd, 1000000.0)
src_start_d3 = _date_digit(source_start_ymd, 100000.0)
src_start_d4 = _date_digit(source_start_ymd, 10000.0)
src_start_d5 = _date_digit(source_start_ymd, 1000.0)
src_start_d6 = _date_digit(source_start_ymd, 100.0)
src_start_d7 = _date_digit(source_start_ymd, 10.0)
src_start_d8 = _date_digit(source_start_ymd, 1.0)
src_end_d1 = _date_digit(source_anchor_ymd, 10000000.0)
src_end_d2 = _date_digit(source_anchor_ymd, 1000000.0)
src_end_d3 = _date_digit(source_anchor_ymd, 100000.0)
src_end_d4 = _date_digit(source_anchor_ymd, 10000.0)
src_end_d5 = _date_digit(source_anchor_ymd, 1000.0)
src_end_d6 = _date_digit(source_anchor_ymd, 100.0)
src_end_d7 = _date_digit(source_anchor_ymd, 10.0)
src_end_d8 = _date_digit(source_anchor_ymd, 1.0)

if show_source_date_on_match:
    ss1 = fit_pass & (abs(x_age - (lookback_bars - 1.0)) < 0.5)
    ss2 = fit_pass & (abs(x_age - (lookback_bars - 2.0)) < 0.5)
    ss3 = fit_pass & (abs(x_age - (lookback_bars - 3.0)) < 0.5)
    ss4 = fit_pass & (abs(x_age - (lookback_bars - 4.0)) < 0.5)
    ss5 = fit_pass & (abs(x_age - (lookback_bars - 5.0)) < 0.5)
    ss6 = fit_pass & (abs(x_age - (lookback_bars - 6.0)) < 0.5)
    ss7 = fit_pass & (abs(x_age - (lookback_bars - 7.0)) < 0.5)
    ss8 = fit_pass & (abs(x_age - (lookback_bars - 8.0)) < 0.5)
    ss9 = fit_pass & (abs(x_age - (lookback_bars - 9.0)) < 0.5)
    ss10 = fit_pass & (abs(x_age - (lookback_bars - 10.0)) < 0.5)
    if lookback_bars >= 24:
        se1 = fit_pass & (abs(x_age - 9.0) < 0.5)
        se2 = fit_pass & (abs(x_age - 8.0) < 0.5)
        se3 = fit_pass & (abs(x_age - 7.0) < 0.5)
        se4 = fit_pass & (abs(x_age - 6.0) < 0.5)
        se5 = fit_pass & (abs(x_age - 5.0) < 0.5)
        se6 = fit_pass & (abs(x_age - 4.0) < 0.5)
        se7 = fit_pass & (abs(x_age - 3.0) < 0.5)
        se8 = fit_pass & (abs(x_age - 2.0) < 0.5)
        se9 = fit_pass & (abs(x_age - 1.0) < 0.5)
        se10 = fit_pass & is_last
    else:
        se1 = _false
        se2 = _false
        se3 = _false
        se4 = _false
        se5 = _false
        se6 = _false
        se7 = _false
        se8 = _false
        se9 = _false
        se10 = _false
else:
    ss1 = _false
    ss2 = _false
    ss3 = _false
    ss4 = _false
    ss5 = _false
    ss6 = _false
    ss7 = _false
    ss8 = _false
    ss9 = _false
    ss10 = _false
    se1 = _false
    se2 = _false
    se3 = _false
    se4 = _false
    se5 = _false
    se6 = _false
    se7 = _false
    se8 = _false
    se9 = _false
    se10 = _false

date_digit_positions = ss1 | ss2 | ss3 | ss4 | ss6 | ss7 | ss9 | ss10 | se1 | se2 | se3 | se4 | se6 | se7 | se9 | se10
date_dash_positions = ss5 | ss8 | se5 | se8
date_digit_value = iff(ss1, src_start_d1, 0.0) + iff(ss2, src_start_d2, 0.0) + iff(ss3, src_start_d3, 0.0) + iff(ss4, src_start_d4, 0.0) + iff(ss6, src_start_d5, 0.0) + iff(ss7, src_start_d6, 0.0) + iff(ss9, src_start_d7, 0.0) + iff(ss10, src_start_d8, 0.0) + iff(se1, src_end_d1, 0.0) + iff(se2, src_end_d2, 0.0) + iff(se3, src_end_d3, 0.0) + iff(se4, src_end_d4, 0.0) + iff(se6, src_end_d5, 0.0) + iff(se7, src_end_d6, 0.0) + iff(se9, src_end_d7, 0.0) + iff(se10, src_end_d8, 0.0)
start_date_region = ss1 | ss2 | ss3 | ss4 | ss5 | ss6 | ss7 | ss8 | ss9 | ss10
date_y = iff(start_date_region, match_start_price + marker_gap_last * 1.15, match_endpoint + marker_gap_last * 1.15)
date_0 = date_digit_positions & (date_digit_value == 0.0)
date_1 = date_digit_positions & (date_digit_value == 1.0)
date_2 = date_digit_positions & (date_digit_value == 2.0)
date_3 = date_digit_positions & (date_digit_value == 3.0)
date_4 = date_digit_positions & (date_digit_value == 4.0)
date_5 = date_digit_positions & (date_digit_value == 5.0)
date_6 = date_digit_positions & (date_digit_value == 6.0)
date_7 = date_digit_positions & (date_digit_value == 7.0)
date_8 = date_digit_positions & (date_digit_value == 8.0)
date_9 = date_digit_positions & (date_digit_value == 9.0)

if show_reference_window:
    reference_draw = reference_mask
else:
    reference_draw = _false

# Quality label bins. These are diagnostic similarity ranges, not forecast
# probabilities.
if show_quality_label:
    fit_00_10 = is_last & fit_pass & (selected_fit < 10.0)
    fit_10_20 = is_last & fit_pass & (selected_fit >= 10.0) & (selected_fit < 20.0)
    fit_20_30 = is_last & fit_pass & (selected_fit >= 20.0) & (selected_fit < 30.0)
    fit_30_40 = is_last & fit_pass & (selected_fit >= 30.0) & (selected_fit < 40.0)
    fit_40_50 = is_last & fit_pass & (selected_fit >= 40.0) & (selected_fit < 50.0)
    fit_50_60 = is_last & fit_pass & (selected_fit >= 50.0) & (selected_fit < 60.0)
    fit_60_70 = is_last & fit_pass & (selected_fit >= 60.0) & (selected_fit < 70.0)
    fit_70_80 = is_last & fit_pass & (selected_fit >= 70.0) & (selected_fit < 80.0)
    fit_80_90 = is_last & fit_pass & (selected_fit >= 80.0) & (selected_fit < 90.0)
    fit_90_100 = is_last & fit_pass & (selected_fit >= 90.0)
    no_match_label = is_last & ((~has_candidate) | (selected_fit < min_fit_score))
else:
    fit_00_10 = _false
    fit_10_20 = _false
    fit_20_30 = _false
    fit_30_40 = _false
    fit_40_50 = _false
    fit_50_60 = _false
    fit_60_70 = _false
    fit_70_80 = _false
    fit_80_90 = _false
    fit_90_100 = _false
    no_match_label = _false

# The client can only scan data actually supplied to the indicator. Display a
# fixed warning when the loaded series is shorter than the requested horizon
# plus the reference template.
loaded_bars = _broadcast_last(bars_count(c))
required_bars = search_history_bars + lookback_bars
history_short = is_last & (loaded_bars < required_bars)
warning_y = c + marker_gap * 2.8

# ----------------------------- Global plots -------------------------------
# 28 / 50 static plot calls.
plot("Top1 Match", iff(match_draw, selected_match, math.nan), analogue_color, match_style, match_width, 0)
plot("Top1 Projection", iff(projection_draw, selected_projection, math.nan), analogue_color, projection_style, projection_width, projection_bars)
plot_fillcolor("Reference Window", h + marker_gap, l - marker_gap, reference_draw, reference_fill, 0)
plot_text("Match Start Tag", match_start_label, match_start_y, "HIST MATCH START", analogue_color, 1, 0, 0, 0)
plot_text("Match Join Tag", match_join_label, match_join_y, "MATCH END / PROJ", analogue_color, 1, 0, 0, 0)
plot_text("Date 0", date_0, date_y, "0", analogue_color, 1, 0, 0, 0)
plot_text("Date 1", date_1, date_y, "1", analogue_color, 1, 0, 0, 0)
plot_text("Date 2", date_2, date_y, "2", analogue_color, 1, 0, 0, 0)
plot_text("Date 3", date_3, date_y, "3", analogue_color, 1, 0, 0, 0)
plot_text("Date 4", date_4, date_y, "4", analogue_color, 1, 0, 0, 0)
plot_text("Date 5", date_5, date_y, "5", analogue_color, 1, 0, 0, 0)
plot_text("Date 6", date_6, date_y, "6", analogue_color, 1, 0, 0, 0)
plot_text("Date 7", date_7, date_y, "7", analogue_color, 1, 0, 0, 0)
plot_text("Date 8", date_8, date_y, "8", analogue_color, 1, 0, 0, 0)
plot_text("Date 9", date_9, date_y, "9", analogue_color, 1, 0, 0, 0)
plot_text("Date Dash", date_dash_positions, date_y, "-", analogue_color, 1, 0, 0, 0)
plot_text("Fit 00 10", fit_00_10, selected_projection, "TOP1 0-10%", weak_color, 1, 0, 0, projection_bars)
plot_text("Fit 10 20", fit_10_20, selected_projection, "TOP1 10-20%", weak_color, 1, 0, 0, projection_bars)
plot_text("Fit 20 30", fit_20_30, selected_projection, "TOP1 20-30%", weak_color, 1, 0, 0, projection_bars)
plot_text("Fit 30 40", fit_30_40, selected_projection, "TOP1 30-40%", weak_color, 1, 0, 0, projection_bars)
plot_text("Fit 40 50", fit_40_50, selected_projection, "TOP1 40-50%", weak_color, 1, 0, 0, projection_bars)
plot_text("Fit 50 60", fit_50_60, selected_projection, "TOP1 50-60%", weak_color, 1, 0, 0, projection_bars)
plot_text("Fit 60 70", fit_60_70, selected_projection, "TOP1 60-70%", moderate_color, 1, 0, 0, projection_bars)
plot_text("Fit 70 80", fit_70_80, selected_projection, "TOP1 70-80%", moderate_color, 1, 0, 0, projection_bars)
plot_text("Fit 80 90", fit_80_90, selected_projection, "TOP1 80-90%", strong_color, 1, 0, 0, projection_bars)
plot_text("Fit 90 100", fit_90_100, selected_projection, "TOP1 90-100%", strong_color, 1, 0, 0, projection_bars)
plot_text("No Good Match", no_match_label, c + marker_gap, "NO GOOD ANALOG", neutral_color, 1, 0, 0, 0)
plot_text("History Short", history_short, warning_y, "LOADED HISTORY < TARGET", warning_color, 1, 0, 0, 0)

output_parameter(
    exhaustive_scan=c * 0.0 + 1.0,
    requested_history_bars=c * 0.0 + search_history_bars,
    loaded_history_bars=loaded_bars,
    full_history_loaded=loaded_bars >= required_bars,
    selected_anchor_offset=selected_anchor_age,
    selected_fit_score=selected_fit,
    selected_distance=selected_distance,
    similarity_mode=c * 0.0 + similarity_mode,
    source_start_bar_age=selected_anchor_age + lookback_bars - 1,
    source_anchor_bar_age=selected_anchor_age,
    source_end_bar_age=selected_anchor_age - projection_bars,
    source_start_ymd=source_start_ymd,
    source_anchor_ymd=source_anchor_ymd,
    source_end_ymd=source_end_ymd,
    projected_end=projection_end,
    projected_bullish=projected_bullish,
    fit_pass=fit_pass,
)
