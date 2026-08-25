# Changelog

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

