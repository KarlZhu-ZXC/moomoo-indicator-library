# MyLang capability probes

## `MYLANG_CONST_PROBE.mylang`

Purpose: determine whether the tested moomoo MyLang runtime supports `CONST()` as a last-value broadcaster.

Expected chart:

- red dotted line: rolling 20-bar high and therefore allowed to change;
- green solid line: one horizontal value across the latest 20 bars;
- `CONST` label on the final bar.

Interpretation:

- compile error on `CONST`: high-fidelity current-only dynamic Fib grids are not available through this route;
- green line is horizontal: the OTE MyLang staircase can be replaced with a current-only grid;
- green line still steps: `CONST` compiles but does not provide the required broadcast semantics.

Create a MyLang main-chart indicator with abbreviation `CONST_T`. No Parameter Settings entries are required.
