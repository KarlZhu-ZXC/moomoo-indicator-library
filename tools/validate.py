#!/usr/bin/env python3
"""Static checks for moomoo Python custom-indicator constraints."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


PLOT_NAMES = {"plot", "plot_bar", "plot_candle", "plot_fillcolor", "plot_icon", "plot_stickline", "plot_text"}


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
    parent: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent[child] = node

    plots: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or call_name(node) not in PLOT_NAMES:
            continue
        plots.append(node)

        current: ast.AST | None = node
        while current in parent:
            current = parent[current]
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                errors.append(f"{path}:{node.lineno}: plot call is inside a local scope")
                break

        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            if len(node.args[0].value) > 25:
                errors.append(f"{path}:{node.lineno}: plot name exceeds 25 characters")

        if call_name(node) == "plot_stickline" and len(node.args) != 9:
            errors.append(f"{path}:{node.lineno}: plot_stickline must have 9 positional arguments")

    if len(plots) > 50:
        errors.append(f"{path}: {len(plots)} plot calls exceeds the 50-call limit")

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
