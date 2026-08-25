#!/usr/bin/env python3
"""Run moomoo-specific Python and MyLang indicator validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validators import ValidationResult, validate_mylang, validate_python


def discover(root: Path, requested: list[str]) -> list[Path]:
    if requested:
        return [Path(item).resolve() for item in requested]
    return sorted((root / "indicators").rglob("*.py")) + sorted((root / "indicators").rglob("*.mylang"))


def validate_path(path: Path) -> ValidationResult:
    if path.suffix == ".py":
        return validate_python(path)
    if path.suffix == ".mylang":
        return validate_mylang(path)
    raise ValueError(f"unsupported indicator language: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", help="Optional .py or .mylang files; defaults to indicators/**")
    parser.add_argument("--strict-warnings", action="store_true", help="Treat environment warnings as failures")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    results = [validate_path(path) for path in discover(root, args.paths)]
    errors = 0
    warnings = 0

    for result in results:
        try:
            shown = result.path.relative_to(root)
        except ValueError:
            shown = result.path
        budget = f"; estimated draws {result.draw_calls}/50" if result.language == "MyLang" else f"; plots {result.draw_calls}/50"
        print(f"{shown}: {result.language} PRECHECK{budget}")
        for finding in result.findings:
            print(finding.render(root))
        errors += len(result.errors)
        warnings += len(result.warnings)

    print(f"Validation complete: {len(results)} files, {errors} errors, {warnings} warnings.")
    if errors or (args.strict_warnings and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
