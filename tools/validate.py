#!/usr/bin/env python3
"""Static checks for moomoo Python and MyLang custom indicators."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


PLOT_NAMES = {"plot", "plot_bar", "plot_candle", "plot_fillcolor", "plot_icon", "plot_stickline", "plot_text"}
MYLANG_DRAW = re.compile(r"\b(?:DRAWLINE|DRAWTEXT|DRAWICON|DRAWNUMBER|STICKLINE|FILLRGN)\s*\(", re.IGNORECASE)
MYLANG_OUTPUT = re.compile(r"^\s*[A-Za-z][A-Za-z0-9_]*\s*:(?!=)", re.MULTILINE)
MYLANG_RGBA = re.compile(r"\bCOLOR[0-9A-Fa-f]{8}\b")


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


def validate_mylang(path: Path) -> list[str]:
    """Parser-independent preflight checks; the moomoo client is authoritative."""
    errors: list[str] = []
    source = path.read_text(encoding="utf-8")
    code_lines = []
    for line_number, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if not stripped or (stripped.startswith("{") and stripped.endswith("}")):
            continue
        code_lines.append((line_number, stripped))
        if not stripped.endswith(";"):
            errors.append(f"{path}:{line_number}: MyLang statement must end with semicolon")

    if source.count("(") != source.count(")"):
        errors.append(f"{path}: unbalanced parentheses")
    if MYLANG_RGBA.search(source):
        errors.append(f"{path}: 8-digit COLORRRGGBBAA is rejected by the tested MyLang client")

    draw_calls = len(MYLANG_DRAW.findall(source)) + len(MYLANG_OUTPUT.findall(source))
    if draw_calls > 50:
        errors.append(f"{path}: {draw_calls} estimated drawing calls exceeds the observed 50-call ceiling")

    repository_root = Path(__file__).resolve().parents[1]
    print(f"{path.relative_to(repository_root)}: MyLang PRECHECK; estimated draws {draw_calls}/50")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []
    for path in sorted((root / "indicators").rglob("*.py")):
        errors.extend(validate(path))
    for path in sorted((root / "indicators").rglob("*.mylang")):
        errors.extend(validate_mylang(path))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("All static checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
