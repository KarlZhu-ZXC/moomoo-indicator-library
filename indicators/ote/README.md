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

## Trading-process boundary

OTE identifies a pullback location; it is not a Buy/Sell signal. A disciplined workflow still requires higher-timeframe direction, independent right-side structure confirmation, a defined loss boundary, a target, and acceptable risk/reward. If price never retraces into the zone, the default action is no chase and no action.

This is an independent implementation of the commonly taught ICT-style OTE Fibonacci framework. Its pivot/shift, dynamic-stretching, and visual behavior are informed by the public description of [Smart Money Fibonacci OTE Engine [ChartPrime]](https://www.tradingview.com/script/iR7drqnn-Smart-Money-Fibonacci-OTE-Engine-ChartPrime/). No ChartPrime Pine source code is included or copied.

OTE is not part of LuxAlgo Smart Money Concepts. This project is not affiliated with ICT, ChartPrime, LuxAlgo, TradingView, moomoo, or Futu.
