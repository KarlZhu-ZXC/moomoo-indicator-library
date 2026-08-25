# Attribution and modification notice

This repository is an adapted work based on **Smart Money Concepts (SMC) [LuxAlgo]**, © LuxAlgo.

## Original work

- Author: LuxAlgo
- Title: Smart Money Concepts (SMC) [LuxAlgo]
- Official publication: https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/
- Source baseline used for this port: https://github.com/deepentropy/lightweight-charts-indicators/blob/31756c8615aff4cefe9cf97350e78bd427f663cd/docs/official/indicators_community/Smart%20Money%20Concepts%20%28SMC%29%20%5BLuxAlgo%5D.pine
- Baseline commit: `31756c8615aff4cefe9cf97350e78bd427f663cd`
- Original license: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International

## Modifications in this repository

The Pine v5 indicator was adapted for the moomoo Python custom-indicator runtime. The work was split into Structure, Order Blocks, and Imbalance modules; Pine object state was rebuilt with static sequence operations; rendering was adapted to moomoo's 50-plot limit; and additional label-spacing and OB/FVG label controls were added.

The implementation is not a line-for-line translation and does not include a copy of the upstream Pine source. Refer to the pinned source link above for the original work.

## No affiliation

This is an unofficial community adaptation. It is not affiliated with, endorsed by, or sponsored by LuxAlgo, TradingView, moomoo, or Futu. All product names and trademarks belong to their respective owners.

