#!/usr/bin/env python3
"""Static checks for moomoo Python custom-indicator constraints."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


PLOT_NAMES = {
    "plot",
    "plot_bar",
    "plot_candle",
    "plot_candlestick",
    "plot_fillcolor",
    "plot_hline",
    "plot_icon",
    "plot_stickline",
    "plot_text",
}
BANNED_GLOBAL_CALLS = {"tr", "smma", "mod", "weekofyear"}
CALENDAR_CALLS_REQUIRE_SOURCE = {"year", "month", "day"}
FORBIDDEN_PLOT_PARENTS = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.For,
    ast.While,
    ast.If,
    ast.With,
    ast.Try,
    ast.Lambda,
    ast.ListComp,
    ast.DictComp,
    ast.SetComp,
    ast.GeneratorExp,
)


def call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imported_modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    parent: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent[child] = node

    plots: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = call_name(node)
        if isinstance(node.func, ast.Name) and name in BANNED_GLOBAL_CALLS:
            errors.append(f"{path}:{node.lineno}: unsupported unqualified runtime call {name}()")
        if isinstance(node.func, ast.Name) and name in CALENDAR_CALLS_REQUIRE_SOURCE and len(node.args) == 0:
            errors.append(f"{path}:{node.lineno}: {name}() requires an explicit source Sequence in the tested runtime")
        if isinstance(node.func, ast.Name) and name in {"floor", "math_log"} and "fmath" not in imported_modules:
            errors.append(f"{path}:{node.lineno}: {name}() requires explicit 'from fmath import *'")
        if isinstance(node.func, ast.Name) and name in {"year", "month", "day"} and "fdatetime" not in imported_modules:
            errors.append(f"{path}:{node.lineno}: {name}() requires explicit 'from fdatetime import *'")
        if name not in PLOT_NAMES:
            continue
        plots.append(node)

        current: ast.AST | None = node
        while current in parent:
            current = parent[current]
            if isinstance(current, FORBIDDEN_PLOT_PARENTS):
                errors.append(f"{path}:{node.lineno}: {name} is not at module/global scope")
                break

        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            if len(node.args[0].value) > 25:
                errors.append(f"{path}:{node.lineno}: plot name exceeds 25 characters")

        if call_name(node) == "plot_stickline" and len(node.args) != 9:
            errors.append(f"{path}:{node.lineno}: plot_stickline must have 9 positional arguments")

    if len(plots) > 50:
        errors.append(f"{path}: {len(plots)} plot calls exceeds the 50-call limit")
    if "values[-1]" in source or ".values[-1]" in source:
        errors.append(f"{path}: unsafe Sequence.values[-1] access")
    if "range(0, 501)" in source or "range(501)" in source:
        errors.append(f"{path}: deep 501-layer Sequence scan reintroduced")

    repository_root = Path(__file__).resolve().parents[1]
    print(f"{path.relative_to(repository_root)}: syntax PASS; plots {len(plots)}/50")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []
    for path in sorted((root / "indicators").rglob("*.py")):
        errors.extend(validate(path))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("All static checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
