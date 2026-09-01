# HIST_SIM v2.0.1 provenance

- Source conversation: `6a8811cd-4d64-83ea-817e-0c292598cf6b` (`SMC`)
- Imported archive: `moomoo_historical_similarity_v2_0_1_10y.zip`
- ChatGPT Library timestamp: 2026-09-01 21:14 (Asia/Shanghai)

## Source files

| File | Repository SHA-256 | Note |
|---|---|---|
| `HIST_SIM.py` | `fb98f0972a45bb4946a0ca925e5a6e8c3b70e73b78eebc476c383dfc2a74bb76` | Exact archive match |
| `HIST_SIM_PCT.py` | `a8241c750015e81a1ad70950ee3dbc0782bf9a2bc3592cfbd10dadad16978cae` | Archive file plus explicit `from fmath import *` required by `floor()` date rendering |

The archive did not include a checksum manifest. Both editions were independently parsed, counted at 28/50 plots and executed through the repository's simulated moomoo Sequence runtime.

## Client compatibility fix

The main edition already imports `fmath` and uses `math_log(x, 2.718281828459045)` because the referenced client did not expose bare `ln()`. The percentage fallback called `floor()` for date digits without importing `fmath`; repository simulation found and corrected that runtime `NameError` before merge.

## Historical regression

The 2026-09-01 integration run queried forward-adjusted daily histories from the user's running moomoo OpenD for QCOM, TTWO, ORCL, AAPL, NVDA, TSLA, SPY and QQQ. Raw OHLC data is not committed. Derived match metadata, candidate counts and SHA-256 content fingerprints are stored in `HIST_SIM_V2_0_1_REGRESSION.json`.
