# Changelog

## Unreleased

- Added an experimental standalone MyLang edition of OTE as `OTE_ML`.
- Split moomoo environment validation into dedicated Python and MyLang validators.
- Added regression tests and a documented rule catalog for client-specific parser, runtime, color, naming, scope, and drawing constraints.
- Guarded OTE direction shifts until an opposite pivot exists and added an opt-out debug layer for no-output diagnosis.
- Simplified MyLang OTE v0.2 to refresh on every valid structural HH/LL and disabled origin invalidation during visual validation.
- Removed `COUNT(event,0)` state gates after client testing showed pivots/HH/LL without shift activation; added validator rule `ML204`.

## Library 4.0 — 2026-08-25

- Reorganized the repository as the moomoo Indicator Library.
- Moved Smart Money Concepts into `indicators/smc/`.
- Added standalone `OTE` v1.0 under `indicators/ote/`.
- Implemented HH/LL direction shifts, dynamic Fibonacci stretching, the 61.8%–78.6% OTE zone, and the 70.5% reference.
- Updated validation and CI to discover indicators recursively.

## 3.2 — 2026-08-25

- Added ATR-adaptive label gaps for internal, swing, EQH/EQL and Strong/Weak labels.
- Added `iOB` and `sOB` labels for active order blocks.
- Added direction-colored FVG labels.
- Rebalanced static plot usage to `28/50`, `50/50`, and `46/50` across the three modules.
- Added the complete Chinese SMC guide in Markdown, PDF and DOCX formats.

## 3.1

- Corrected pivot-to-break segment length.
- Added explicit non-null checks before internal/swing level comparisons.
- Rebuilt BOS/CHoCH classification around the prior structure-event direction.

## 3.0

- Rebased the implementation on the pinned LuxAlgo Pine v5 source baseline.
- Split the suite into `SMC_STR`, `SMC_OB`, and `SMC_IMB`.
