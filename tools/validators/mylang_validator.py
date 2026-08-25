from __future__ import annotations

import re
from pathlib import Path

from .common import ValidationResult


DRAW_CALL = re.compile(r"\b(?:DRAWLINE|DRAWTEXT|DRAWICON|DRAWNUMBER|STICKLINE|FILLRGN)\s*\(", re.IGNORECASE)
OUTPUT_LINE = re.compile(r"^\s*[A-Za-z][A-Za-z0-9_]*\s*:(?!=)", re.MULTILINE)
RGBA_COLOR = re.compile(r"\bCOLOR[0-9A-Fa-f]{8}\b")
PREFIX_NOT = re.compile(r"\bNOT\s+[A-Za-z][A-Za-z0-9_]*", re.IGNORECASE)
NEGATIVE_COMPARE = re.compile(r"(?:=|<>)-\d")
ASSIGNMENT = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s*:(?:=|(?!=))", re.MULTILINE)
FUNCTION_CALL = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\s*\(")
IDENTIFIER = re.compile(r"\b[A-Za-z][A-Za-z0-9_]*\b")
DYNAMIC_WINDOW = re.compile(r"\b(?:HHV|LLV)\s*\(\s*[^,]+,\s*([A-Za-z][A-Za-z0-9_]*)\s*\)", re.IGNORECASE)

RESERVED_ASSIGNMENTS = {"NDAY"}
UNSUPPORTED_FUNCTIONS = {"MOD"}
KEYWORDS = {"AND", "OR", "NOT", "IF"}
BUILTIN_SERIES = {
    "C",
    "CLOSE",
    "O",
    "OPEN",
    "H",
    "HIGH",
    "L",
    "LOW",
    "V",
    "VOL",
    "DATE",
    "WEEKDAY",
    "MONTH",
    "YEAR",
    "ISLASTBAR",
    "CURRBARSCOUNT",
    "BARSCOUNT",
    "DRAWNULL",
}
STYLE_WORDS = {"DOTLINE", "LINETHICK1", "LINETHICK2", "LINETHICK3", "LINETHICK4", "LINETHICK5"}


def _strip_comments_and_strings(source: str) -> str:
    without_comments = re.sub(r"\{.*?\}", "", source, flags=re.DOTALL)
    return re.sub(r"'(?:''|[^'])*'", "''", without_comments)


def _delimiter_error(source: str) -> tuple[int, str] | None:
    stack: list[tuple[str, int]] = []
    pairs = {")": "("}
    in_string = False
    in_comment = False
    for line_number, line in enumerate(source.splitlines(), 1):
        for char in line:
            if char == "'" and not in_comment:
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                in_comment = True
                continue
            if char == "}" and in_comment:
                in_comment = False
                continue
            if in_comment:
                continue
            if char == "(":
                stack.append((char, line_number))
            elif char == ")":
                if not stack or stack[-1][0] != pairs[char]:
                    return line_number, "unmatched closing parenthesis"
                stack.pop()
    if stack:
        return stack[-1][1], "unclosed opening parenthesis"
    return None


def validate_mylang(path: Path) -> ValidationResult:
    result = ValidationResult(path=path, language="MyLang")
    source = path.read_text(encoding="utf-8")
    code = _strip_comments_and_strings(source)

    for line_number, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if not stripped or (stripped.startswith("{") and stripped.endswith("}")):
            continue
        if not stripped.endswith(";"):
            result.add(line_number, "ML101", "ERROR", "statement must end with semicolon")

    delimiter = _delimiter_error(source)
    if delimiter:
        result.add(delimiter[0], "ML102", "ERROR", delimiter[1])
    if RGBA_COLOR.search(code):
        result.add(0, "ML103", "ERROR", "8-digit COLORRRGGBBAA is rejected by the tested client")
    if PREFIX_NOT.search(code):
        result.add(0, "ML104", "ERROR", "prefix NOT in compound expressions caused parser errors; compare with zero")
    if NEGATIVE_COMPARE.search(code):
        result.add(0, "ML105", "ERROR", "avoid unary negative literals beside comparison operators")

    assigned = {name.upper() for name in ASSIGNMENT.findall(code)}
    for name in sorted(assigned & RESERVED_ASSIGNMENTS):
        line = next((i for i, text in enumerate(source.splitlines(), 1) if re.match(rf"\s*{name}\s*:", text, re.I)), 0)
        result.add(line, "ML106", "ERROR", f"{name} conflicts with a tested client reserved/system name")

    functions = {name.upper() for name in FUNCTION_CALL.findall(code)}
    for name in sorted(functions & UNSUPPORTED_FUNCTIONS):
        result.add(0, "ML107", "ERROR", f"unsupported tested MyLang function: {name}(...)")

    dynamic_names = {name.upper() for name in DYNAMIC_WINDOW.findall(code)}
    for name in sorted(dynamic_names):
        result.add(
            0,
            "ML201",
            "WARNING",
            f"dynamic HHV/LLV period '{name}' requires real moomoo client validation",
        )

    known = assigned | functions | KEYWORDS | BUILTIN_SERIES | STYLE_WORDS
    identifiers = {name.upper() for name in IDENTIFIER.findall(code)}
    external = sorted(
        name
        for name in identifiers - known
        if not name.startswith("COLOR") and not name.startswith("LINETHICK")
    )
    for name in external:
        result.add(0, "ML202", "WARNING", f"'{name}' is not assigned in source; define it in Parameter Settings if intentional")

    result.draw_calls = len(DRAW_CALL.findall(code)) + len(OUTPUT_LINE.findall(code))
    if result.draw_calls > 50:
        result.add(
            0,
            "ML203",
            "WARNING",
            f"estimated {result.draw_calls} drawing calls; the 50-call limit is verified for Python, not yet for MyLang",
        )
    return result
