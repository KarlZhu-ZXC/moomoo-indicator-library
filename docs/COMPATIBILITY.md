# Compatibility matrix

| Capability | Status | Notes |
|---|---|---|
| Internal structure | Source-aligned | Internal pivot length fixed at 5, following the baseline Pine script |
| Swing structure | Source-aligned | Configurable swing length; default 50 |
| BOS / CHoCH | Source-aligned | State-driven classification with pivot-to-break geometry |
| HH / HL / LH / LL | Supported | Optional swing-point labels |
| EQH / EQL | Supported | ATR-threshold comparison and independent segments |
| Strong / Weak High-Low | Adapted | Trailing extremes use an explicit 500-bar scan horizon |
| Internal / Swing OB | Supported | Active blocks, volatility parsing, mitigation and labels |
| FVG | Current timeframe | Arbitrary Pine `request.security()` timeframe is unavailable |
| Premium / Equilibrium / Discount | Supported | Uses the trailing swing range |
| Previous D/W/M High-Low | Not included | Calendar/timeframe facilities were not available in the client-confirmed runtime |
| Pine dynamic objects | Visual equivalent | Rebuilt with static moomoo plot channels |
| Present mode | Adapted | Subject to static object/rendering semantics |

## Client constraints reflected in the implementation

- Plot functions must remain at module/global scope.
- A custom indicator may use at most 50 static plot calls.
- Plot names are limited to 25 characters.
- `plot_stickline` uses the client-confirmed nine-argument signature.
- Disconnected `plot()` runs may be joined; independent structure segments therefore use stickline primitives.

The files pass ordinary Python syntax compilation and repository-level static checks. The moomoo desktop client remains the authoritative compiler and renderer because `ftool` is provided by that environment.

