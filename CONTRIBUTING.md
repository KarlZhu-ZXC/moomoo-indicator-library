# Contributing

Bug reports are most useful when they include:

- moomoo desktop version and operating system;
- indicator module and complete first error message;
- symbol, chart timeframe, and relevant parameter values;
- screenshots from both moomoo and the reference TradingView script when reporting fidelity differences.

Please preserve the attribution applicable to each collection: LuxAlgo attribution in `indicators/smc/`, and the independent-implementation/ChartPrime behavior-reference notice in `indicators/ote/`. Contributions must remain non-commercial and be shared under CC BY-NC-SA 4.0.

When a moomoo client error reveals a new environment-specific restriction, add a minimal regression test and language-specific validator rule before fixing the indicator. See [`tools/VALIDATION_RULES.md`](tools/VALIDATION_RULES.md).
