# ChartPrime Optimal Trade Entry (`OTE_CP`)

Memory-bounded moomoo Python port of **Smart Money Fibonacci OTE Engine [ChartPrime]**.

## Installation

Create a Python main-chart indicator named `OTE_CP` and paste the complete contents of [`OTE_CP.py`](OTE_CP.py).

## v4.1 features

- symmetric confirmed pivots with default `Pivot Length = 10`;
- HH/LL direction shifts and structure lines;
- SH/SL text for ordinary confirmed swings;
- dynamic high/low anchor stretching;
- current Fibonacci grid and swing diagonal;
- customizable 0.618–0.786 OTE zone;
- pale-yellow alpha fill and fixed OTE label;
- optional latest two completed previous Fib sets;
- output parameters for shift events, anchors, direction, OTE bounds and Fib values.

## Important defaults

| Parameter | Default |
|---|---:|
| Pivot Length | 10 |
| Show Swing Markers | True |
| Show SH/SL Text | True |
| Show HH/LL Shift Lines | True |
| Show OTE Zone | True |
| Show Fib Levels | True |
| Show Swing Diagonal | True |
| Show Previous Fibs | False |
| OTE Lower / Upper | 0.618 / 0.786 |

## Reference behavior

When one confirmation bar qualifies as both HH and LL, the bullish branch is processed first and the bearish branch second. Both event outputs remain true while final direction becomes bearish. v4.1 preserves that execution order.

Continued pivots in the active direction stretch the anchor. Previous-object graph construction is skipped entirely when `Show Previous Fibs = False`.

## moomoo visual equivalents

- Pine dynamic objects are recreated through bounded static channels.
- Previous history is limited to the latest two completed Fib sets.
- Dynamic numeric strings cannot be passed to `plot_text()`; prices remain visible through legend/hover/output parameters.
- Anchor searches are bounded to the latest 500 bars.

## Trading-process boundary

OTE identifies a pullback location, not a Buy/Sell instruction. A zone touch requires independent direction, right-side confirmation, a loss boundary, target and acceptable risk/reward. No retracement means no chase and no action.

## Attribution

Original concept/source: **Smart Money Fibonacci OTE Engine [ChartPrime]**, open-source Pine Script, MPL-2.0. This independent moomoo platform port preserves attribution. See [LICENSE.md](LICENSE.md) and the repository [NOTICE](../../NOTICE.md).
