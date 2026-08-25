from __future__ import annotations

import ast
import re
from pathlib import Path

from .common import ValidationResult


PLOT_NAMES = {
    "plot",
    "plot_bar",
    "plot_candle",
    "plot_fillcolor",
    "plot_icon",
    "plot_stickline",
    "plot_text",
}

# These names were rejected as global functions/variables in the tested moomoo
# Python indicator runtime. Sequence methods such as series.smma(...) remain OK.
UNSUPPORTED_GLOBAL_CALLS = {"mod", "tr", "smma", "year", "month", "day", "weekofyear"}
LEADING_VECTOR_OPERATOR = re.compile(r"^\s*[&|]")


def call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _known_scalar_names(tree: ast.AST) -> set[str]:
    scalars: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if isinstance(node.value, ast.Constant):
                scalars.add(node.targets[0].id)
            if isinstance(node.value, ast.Call) and call_name(node.value) == "input_parameter":
                scalars.add(node.targets[0].id)
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            if isinstance(node.iter, ast.Call) and call_name(node.iter) == "range":
                scalars.add(node.target.id)
    return scalars


def _is_scalar_expression(node: ast.AST, scalar_names: set[str]) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id not in scalar_names:
            return False
        if isinstance(child, (ast.Call, ast.Attribute, ast.Subscript)):
            return False
    return True


def validate_python(path: Path) -> ValidationResult:
    result = ValidationResult(path=path, language="Python")
    source = path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        result.add(exc.lineno or 0, "PY001", "ERROR", f"standard Python syntax error: {exc.msg}")
        return result

    parents = _parent_map(tree)
    scalar_names = _known_scalar_names(tree)
    plots: list[ast.Call] = []

    for line_number, line in enumerate(source.splitlines(), 1):
        if LEADING_VECTOR_OPERATOR.search(line):
            result.add(
                line_number,
                "PY106",
                "ERROR",
                "tested moomoo parser rejects continuation lines beginning with '&' or '|'",
            )

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = call_name(node)
            if isinstance(node.func, ast.Name) and name in UNSUPPORTED_GLOBAL_CALLS:
                result.add(node.lineno, "PY105", "ERROR", f"unsupported tested global call: {name}(...)")
            if name not in PLOT_NAMES:
                continue

            plots.append(node)
            current: ast.AST | None = node
            while current in parents:
                current = parents[current]
                if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    result.add(node.lineno, "PY101", "ERROR", "plot call is inside a local scope")
                    break

            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                if len(node.args[0].value) > 25:
                    result.add(node.lineno, "PY103", "ERROR", "plot name exceeds 25 characters")

            if name == "plot_stickline" and len(node.args) != 9:
                result.add(node.lineno, "PY104", "ERROR", "plot_stickline must have 9 positional arguments")

        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.BitAnd, ast.BitOr)):
            left_scalar = _is_scalar_expression(node.left, scalar_names)
            right_scalar = _is_scalar_expression(node.right, scalar_names)
            if left_scalar != right_scalar:
                result.add(
                    node.lineno,
                    "PY201",
                    "WARNING",
                    "possible scalar-bool and Sequence bitwise mix; tested client requires Sequence operands",
                )

    result.draw_calls = len(plots)
    if result.draw_calls > 50:
        result.add(0, "PY102", "ERROR", f"{result.draw_calls} plot calls exceeds the verified 50-call limit")
    return result

