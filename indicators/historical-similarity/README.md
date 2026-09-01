# Historical Similarity Projection (`HIST_SIM`)

Exhaustive normalized-path analogue search for the moomoo Python custom-indicator runtime.

## Files

- [`HIST_SIM.py`](HIST_SIM.py): primary logarithmic/percentage edition using `math_log()` from `fmath`.
- [`HIST_SIM_PCT.py`](HIST_SIM_PCT.py): percentage-only compatibility fallback with no logarithm dependency.

## Defaults

| Parameter | Default | Meaning |
|---|---:|---|
| Lookback Window | 50 | Current and historical path length |
| Projection Length | 20 | Realized continuation bars |
| Search History Bars | 2520 | Approximate ten trading years on a daily chart |
| Similarity 0Pct1Log | 1 | Cumulative log-path mode |
| Recent Emphasis Bars | 10 | Tail segment receiving extra weight |
| Recent Weight | 1.0 | Tail-path weight |
| Last Bar Shock Weight | 2.0 | Final return-gap weight |
| Min Fit Score | 60 | Minimum diagnostic similarity score |

## Search behavior

With the defaults and sufficient data, the indicator evaluates every eligible historical anchor from 71 to 2520 bars ago—approximately 2,450 candidate windows. It does not sample 48 fixed offsets.

The graph contains one distance sequence and uses native `llv()` / `llv_bars()` to select the best anchor. Search depth therefore does not create one calculation branch per candidate.

Similarity compares normalized relative paths rather than absolute prices:

```text
Log mode: 100 × ln(Price / WindowStartPrice)
Pct mode: 100 × (Price / WindowStartPrice - 1)
```

The blue dashed segment is the selected historical match mapped onto the current price axis. The blue solid segment is what actually happened after that historical window. The two segments are one continuous historical analogue, not a probability forecast.

## Data coverage

The client must supply at least `Search History Bars + Lookback Window` valid bars. Outputs include:

- `requested_history_bars`
- `loaded_history_bars`
- `full_history_loaded`
- selected source dates, fit score and projection direction

When data is short, the chart displays `LOADED HISTORY < TARGET`; the result then covers only the history actually loaded.

## Installation

Create a Python main-chart indicator named `HIST_SIM` and paste [`HIST_SIM.py`](HIST_SIM.py). If `math_log()` is unavailable in the installed client, use [`HIST_SIM_PCT.py`](HIST_SIM_PCT.py).

## Interpretation boundary

The fit score is a custom path-similarity diagnostic, not an estimated probability of future direction. Historical analogues can fail because regimes, volatility, fundamentals and event risk differ. Treat the projected segment as a scenario for review, not an entry or trade instruction.

## Multi-symbol regression

The repository includes derived ten-year regression results for `QCOM`, `TTWO`, `ORCL`, `AAPL`, `NVDA`, `TSLA`, `SPY` and `QQQ`. Every symbol loaded 2,808 daily bars and evaluated 2,450 anchors in both log and percentage modes.

To refresh the integration snapshot with a running OpenD and `moomoo-api`:

```bash
python tools/integration/hist_sim_regression.py \
  --json-output docs/releases/HIST_SIM_V2_0_1_REGRESSION.json \
  --markdown-output docs/releases/HIST_SIM_V2_0_1_REGRESSION.md
```

Raw OHLC is not committed; only derived metadata and data hashes are stored.

## License

Original repository contribution, distributed under CC BY-NC-SA 4.0. See [LICENSE.md](LICENSE.md) and the repository notice.
