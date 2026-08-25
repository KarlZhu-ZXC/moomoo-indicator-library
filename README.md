# moomoo Indicator Library

<p align="center">
  <strong>Open-source technical-analysis indicators for the moomoo Python custom-indicator runtime</strong><br>
  Smart Money Concepts · Optimal Trade Entry · More modules to come
</p>

<p align="center">
  <img alt="Library 4.0" src="https://img.shields.io/badge/library-4.0-089981?style=for-the-badge">
  <img alt="moomoo" src="https://img.shields.io/badge/platform-moomoo-00C805?style=for-the-badge">
  <img alt="Python" src="https://img.shields.io/badge/language-Python-3178C6?style=for-the-badge">
  <img alt="CC BY-NC-SA 4.0" src="https://img.shields.io/badge/license-CC_BY--NC--SA_4.0-F23645?style=for-the-badge">
</p>

> [!IMPORTANT]
> These are unofficial community indicators. They are built for education, research, and chart analysis—not automatic trading. The moomoo Desktop client remains the authoritative compiler and renderer.

## Indicator catalog

| Collection | Indicators | Status | Description |
|---|---|---|---|
| [Smart Money Concepts](indicators/smc/) | `SMC_STR`, `SMC_OB`, `SMC_IMB` | Stable · v3.2 | Structure, BOS/CHoCH, Order Blocks, FVGs, EQH/EQL, and value zones |
| [Optimal Trade Entry](indicators/ote/) | `OTE`, `OTE_ML` | Python v1.0 · MyLang experimental | HH/LL direction-shift Fibonacci grid with a dynamic 61.8%–78.6% zone |

## Quick installation

1. Open **Indicator Management** in moomoo Desktop.
2. Create a new **Python overlay indicator**.
3. Copy one indicator file in full into the editor.
4. Use the short name shown below, then run **Test** and **Apply**.

| Short name | File |
|---|---|
| `OTE` | [`indicators/ote/OTE.py`](indicators/ote/OTE.py) |
| `OTE_ML` | [`indicators/ote/OTE.mylang`](indicators/ote/OTE.mylang) |
| `SMC_STR` | [`indicators/smc/SMC_STR.py`](indicators/smc/SMC_STR.py) |
| `SMC_OB` | [`indicators/smc/SMC_OB.py`](indicators/smc/SMC_OB.py) |
| `SMC_IMB` | [`indicators/smc/SMC_IMB.py`](indicators/smc/SMC_IMB.py) |

Each file is standalone. OTE is deliberately separate from SMC and does not consume any SMC module's plot budget or state. `OTE.py` is the canonical edition; `OTE.mylang` is an experimental compatibility port for client testing.

## Optimal Trade Entry

`OTE` displays the latest structure-directed Fibonacci grid:

- HH/LL direction-shift recognition
- 61.8% shallow boundary
- 70.5% optimal reference
- 78.6% deep boundary
- bullish or bearish shaded zone
- optional full Fibonacci grid
- dynamic stretching with new trend extremes
- optional structural-origin invalidation

The default pivot length is 5. A swing is confirmed only after the required bars have elapsed, so direction shifts appear with confirmation lag. Once direction exists, the expansion endpoint follows new highs or lows; the OTE zone therefore moves while the trend continues to extend.

> [!CAUTION]
> OTE is a location filter, not an entry command. A zone touch should result in review—not an automatic position change—until direction, right-side confirmation, loss boundary, target, and risk/reward are defined.

See the complete [OTE documentation](indicators/ote/README.md).

## Smart Money Concepts

The SMC collection remains split into three stackable modules because the tested moomoo Desktop Python compiler rejects a script with more than 50 static `plot*()` calls.

| Indicator | Features | Static plot budget |
|---|---|---:|
| `SMC_STR` | Internal/swing structure, BOS, CHoCH, HH/HL/LH/LL, EQH/EQL, Strong/Weak | 28 / 50 |
| `SMC_OB` | Internal/swing Order Blocks, volatility filtering, mitigation, labels | 50 / 50 |
| `SMC_IMB` | Current-timeframe FVGs and Premium/Equilibrium/Discount | 46 / 50 |

<p align="center">
  <img src="docs/smc/assets/fig1_structure.png" alt="Market structure, BOS, and CHoCH diagram" width="900">
</p>

| Liquidity · EQH/EQL | Order Blocks · FVG |
|---|---|
| ![Liquidity](docs/smc/assets/fig2_liquidity.png) | ![Order Blocks and FVG](docs/smc/assets/fig3_ob_fvg.png) |

| Premium · Equilibrium · Discount |
|---|
| ![Premium, equilibrium, and discount zones](docs/smc/assets/fig4_zones.png) |

SMC resources:

- [Collection overview](indicators/smc/README.md)
- [Compatibility matrix](docs/smc/COMPATIBILITY.md)
- [Chinese handbook — Markdown](docs/smc/Smart_Money_Concepts_实战手册_CN.md)
- [Chinese handbook — PDF](docs/smc/Smart_Money_Concepts_实战手册_CN.pdf)
- [Chinese handbook — editable Word](docs/smc/Smart_Money_Concepts_实战手册_CN.docx)

## Client-observed constraints

The repository validator checks behavior observed in the tested moomoo Desktop Python custom-indicator compiler:

- plot functions remain at module/global scope;
- no indicator exceeds 50 static `plot*()` calls;
- plot names contain at most 25 characters;
- `plot_stickline` uses the client-confirmed nine-argument signature.

The 50-call ceiling is client-observed rather than a limit published on moomoo's public website and may change in future versions.

Run all repository checks with:

```bash
python tools/validate.py
```

## Repository layout

```text
indicators/
├── ote/
│   ├── OTE.py
│   ├── OTE.mylang
│   └── README.md
└── smc/
    ├── SMC_STR.py
    ├── SMC_OB.py
    ├── SMC_IMB.py
    └── README.md

docs/
└── smc/
    ├── assets/
    ├── COMPATIBILITY.md
    └── Smart_Money_Concepts_实战手册_CN.*
```

## Attribution

The SMC collection adapts **Smart Money Concepts (SMC) [LuxAlgo]**, © LuxAlgo:

- [Official TradingView publication](https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/)
- [Pinned Pine v5 source baseline](https://github.com/deepentropy/lightweight-charts-indicators/blob/31756c8615aff4cefe9cf97350e78bd427f663cd/docs/official/indicators_community/Smart%20Money%20Concepts%20%28SMC%29%20%5BLuxAlgo%5D.pine)

OTE is an independent implementation of the commonly taught ICT-style Fibonacci retracement framework. Its behavior is informed by the public description of [Smart Money Fibonacci OTE Engine [ChartPrime]](https://www.tradingview.com/script/iR7drqnn-Smart-Money-Fibonacci-OTE-Engine-ChartPrime/); no third-party OTE source code is included.

See [NOTICE.md](NOTICE.md) for the full attribution and modification notice. LuxAlgo, ICT, TradingView, moomoo, and Futu names and trademarks belong to their respective owners. This project is not affiliated with, endorsed by, or sponsored by any of them.

## Risk disclosure

Indicators organize historical OHLC observations. They do not identify institutional orders, predict outcomes, define personal suitability, or replace a complete trade plan. Before any proposed exposure, independently define the decision horizon, direction, confirmation, loss boundary, target, and acceptable risk/reward.

## License

This repository is released under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International**. Preserve attribution, use the material only for non-commercial purposes, and distribute adaptations under the same license. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
