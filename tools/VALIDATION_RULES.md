# moomoo indicator validation rules

The validators encode failures observed in the moomoo Desktop custom-indicator environment. They are not general Python/MyLang linters and cannot replace the proprietary client compiler.

## Workflow for every new client error

1. Save the smallest source fragment that reproduces the error.
2. Add or update a unit test under `tools/tests/`.
3. Add a language-specific rule.
4. Fix the indicator.
5. Run `python -m unittest discover -s tools/tests` and `python tools/validate.py`.
6. Retest in moomoo Desktop and record whether the rule is confirmed or only precautionary.

## Python rules

| Rule | Severity | Tested moomoo behavior |
|---|---|---|
| `PY001` | Error | Standard Python syntax must parse first |
| `PY101` | Error | `plot*()` calls are rejected inside functions/lambdas |
| `PY102` | Error | 51 static plot calls are rejected; 50 is the verified ceiling |
| `PY103` | Error | Plot names longer than 25 characters are rejected |
| `PY104` | Error | `plot_stickline` requires nine positional arguments |
| `PY105` | Error | Known unsupported global calls: `mod`, `tr`, `smma`, calendar functions |
| `PY106` | Error | Continuation lines beginning with `&` or `|` are rejected by the client subset parser |
| `PY201` | Warning | Scalar Python bool mixed with a vector Sequence through `&`/`|` may fail at runtime |

Sequence methods such as `series.smma(...)` are allowed; the rule applies to unsupported global calls such as `smma(...)`.

## MyLang rules

| Rule | Severity | Tested or pending behavior |
|---|---|---|
| `ML101` | Error | Every statement must end with `;` |
| `ML102` | Error | Parentheses must be structurally balanced; reports the nearest line |
| `ML103` | Error | `COLORRRGGBBAA` was rejected; use six-digit colors |
| `ML104` | Error | Prefix `NOT variable` inside compound expressions caused parser errors; compare with zero |
| `ML105` | Error | Negative literals immediately beside comparison operators caused parser issues |
| `ML106` | Error | `NDAY` conflicted with a client system/reserved name |
| `ML107` | Error | `MOD(...)` was rejected by the tested MyLang runtime |
| `ML201` | Warning | Dynamic `HHV/LLV` periods require real-client compilation/render testing |
| `ML202` | Warning | An identifier is not assigned in source and may require Parameter Settings |
| `ML203` | Warning | Estimated drawing calls exceed 50; the ceiling is not yet independently verified for MyLang |
| `ML204` | Warning | `COUNT(event,0)` compiled but was unreliable as an event-existence gate in client testing |

## Commands

```bash
python -m unittest discover -s tools/tests
python tools/validate.py
python tools/validate.py --strict-warnings
python tools/validate.py indicators/ote/OTE.mylang
```

Warnings identify client-dependent behavior. CI reports them but fails only on errors.
