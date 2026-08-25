# Optimal Trade Entry (`OTE`)

Standalone pivot-and-shift Fibonacci retracement engine for the moomoo Python custom-indicator runtime.

## What it draws

- HH/LL direction-shift detection
- Bullish or bearish 61.8%–78.6% OTE zone
- 70.5% optimal reference line
- Optional full `0 / 0.236 / 0.382 / 0.5 / 1.0` Fibonacci grid
- Dynamic stretching when the trend makes new highs or lows
- Direction label at the chart's right edge

The indicator uses confirmed alternating pivots. With `Pivot Length = 5`, a pivot appears only after five bars of confirmation; the zone is not back-painted to the original pivot bar.

## Installation

Create a new Python overlay indicator named `OTE` in moomoo Desktop and paste the complete contents of [`OTE.py`](OTE.py).

An experimental MyLang edition is also available as [`OTE.mylang`](OTE.mylang). Create a MyLang main-chart indicator with:

- abbreviation: `OTE_ML`
- full name: `Smart Money Fib OTE MyLang`
- no Parameter Settings entries required

Edit the constants at the top of the source to change Pivot Length, grid/fill visibility, invalidation, or Fibonacci ratios.

### MyLang experiment boundaries

- The key capability under test is `HHV/LLV` with a dynamic `BARSLAST`-derived period.
- `DEBUG:=1` is enabled during client validation and draws confirmed pivots, direction shifts, and a right-edge state message. Set it to `0` after fidelity is confirmed.
- MyLang v0.2 refreshes its current leg on every confirmed structural HH/LL. This is intentionally simpler than the Python edition's direction-state lifecycle.
- Client testing showed `COUNT(event,0)>0` was not reliable as an event-existence gate, so v0.2 uses `BARSLAST(event)<BARSCOUNT(C)` instead.
- `INVALIDATE:=0` is the validation default so origin lifecycle cannot suppress an otherwise valid first grid. Re-enable it only after Fib rendering is confirmed.
- MyLang draws evolving series rather than Pine-style dynamic horizontal objects, so levels may show their movement as the trend stretches.
- Six-digit colors are used because client testing rejected `COLORRRGGBBAA`.
- `SHOWFILL` defaults to `0`; enable it only if the pastel solid fill does not obscure candles.
- The moomoo client compiler and chart are the final validation. Repository checks are only a parser-independent preflight.

### First client test

1. Keep `SHOWFILL:=0` and compile the script unchanged.
2. If compilation fails, capture the first complete error and line number.
3. If it passes, load `OTE` and `OTE_ML` on the same symbol and timeframe.
4. Compare direction, origin, 0.618/0.705/0.786 values, and behavior after a new trend extreme.
5. Test an origin break and confirm the old grid is hidden when `INVALIDATE:=1`.

Debug interpretation:

- no `PH`/`PL`: pivot detection is the blocker;
- `PH`/`PL` but no `HH`/`LL`: previous-pivot comparison is the blocker;
- `HH`/`LL` but no `UP SHIFT`/`DN SHIFT`: direct shift rendering is the blocker;
- `OTE waiting for HH/LL`: no valid direction shift exists in loaded history;
- `OTE inactive`: a shift exists, but the range is empty or the origin was invalidated.

Do not judge fidelity from screenshots with different Pivot Lengths or chart histories.

## Default parameters

| Parameter | Default | Meaning |
|---|---:|---|
| Pivot Length | 5 | Bars required to confirm a swing |
| OTE Shallow Fib | 0.618 | Shallow zone boundary |
| OTE Optimal Fib | 0.705 | Reference level inside the zone |
| OTE Deep Fib | 0.786 | Deep zone boundary |
| Show Full Fib Grid | True | Draw the non-OTE Fibonacci levels |
| Invalidate Origin Break | True | Hide a grid whose structural origin is breached |

Keep the ratios ordered as `0 < shallow < optimal < deep < 1`.

## Lifecycle

1. A Higher High can establish a bullish direction shift.
2. A Lower Low can establish a bearish direction shift.
3. Repeated HH/LL in the same direction stretch the current grid instead of starting a new one.
4. The latest opposite direction shift replaces the displayed grid.
5. With origin invalidation enabled, a wick beyond the structural origin hides the grid.

Because the expansion endpoint follows new extremes, the grid and OTE zone intentionally move while the trend is extending. That behavior keeps the current retracement mathematically aligned but must not be mistaken for a fixed, non-moving historical signal.

## ChartPrime behavior comparison

| Capability | moomoo `OTE` |
|---|---|
| Pivot-based HH/LL direction shifts | Supported |
| Dynamic stretching with trend extremes | Supported |
| Custom 0.618–0.786 OTE boundaries | Supported |
| 70.5% reference | Supported |
| Full current Fibonacci grid | Supported |
| Structural-origin invalidation | Added safety option |
| Swing diagonal between anchors | Not included; moomoo has no equivalent dynamic line object |
| Previous historical Fib objects | Not included in v1.0; current grid only |
| Price labels beyond the final bar | Not available in the tested runtime |

The comparison table describes the Python edition. The MyLang edition is intentionally experimental and visually simpler.

## Trading-process boundary

OTE identifies a pullback location; it is not a Buy/Sell signal. A disciplined workflow still requires higher-timeframe direction, independent right-side structure confirmation, a defined loss boundary, a target, and acceptable risk/reward. If price never retraces into the zone, the default action is no chase and no action.

This is an independent implementation of the commonly taught ICT-style OTE Fibonacci framework. Its pivot/shift, dynamic-stretching, and visual behavior are informed by the public description of [Smart Money Fibonacci OTE Engine [ChartPrime]](https://www.tradingview.com/script/iR7drqnn-Smart-Money-Fibonacci-OTE-Engine-ChartPrime/). No ChartPrime Pine source code is included or copied.

OTE is not part of LuxAlgo Smart Money Concepts. This project is not affiliated with ICT, ChartPrime, LuxAlgo, TradingView, moomoo, or Futu.
