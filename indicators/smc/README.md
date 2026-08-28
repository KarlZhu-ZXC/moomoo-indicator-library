# Smart Money Concepts (`SMC_*`)

Three stackable v4.1 moomoo Python overlay indicators adapted from the open-source **Smart Money Concepts (SMC) [LuxAlgo]** Pine Script.

| Indicator | Purpose | Plot budget |
|---|---|---:|
| [`SMC_STR.py`](SMC_STR.py) | Structure, BOS/CHoCH, swing points, EQH/EQL, Strong/Weak | 28 / 50 |
| [`SMC_OB.py`](SMC_OB.py) | Internal and swing Order Blocks | 46 / 50 |
| [`SMC_IMB.py`](SMC_IMB.py) | FVG and Premium/Equilibrium/Discount | 31 / 50 |

Create each file as a separate Python overlay indicator in moomoo Desktop, then stack the modules on the same chart.

v4.1 removes the former hundreds-deep Sequence scans, fixes EQH/EQL label y-position, and increases default label gaps without changing BOS/CHoCH event prices or segment endpoints.

See the [v4.1 notes](../../docs/releases/V4_1_CN.md), [compatibility matrix](../../docs/smc/COMPATIBILITY.md), and [Chinese handbook](../../docs/smc/Smart_Money_Concepts_实战手册_CN.md).

The SMC modules retain the LuxAlgo attribution headers and are licensed under CC BY-NC-SA 4.0. They are unofficial and not affiliated with LuxAlgo, TradingView, moomoo, or Futu.
