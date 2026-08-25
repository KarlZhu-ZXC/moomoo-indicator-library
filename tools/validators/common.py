from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


Severity = Literal["ERROR", "WARNING"]


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    rule: str
    severity: Severity
    message: str

    def render(self, root: Path | None = None) -> str:
        try:
            shown = self.path.relative_to(root) if root else self.path
        except ValueError:
            shown = self.path
        location = f"{shown}:{self.line}" if self.line else str(shown)
        return f"{location}: {self.severity} {self.rule}: {self.message}"


@dataclass
class ValidationResult:
    path: Path
    language: str
    findings: list[Finding] = field(default_factory=list)
    draw_calls: int = 0

    @property
    def errors(self) -> list[Finding]:
        return [item for item in self.findings if item.severity == "ERROR"]

    @property
    def warnings(self) -> list[Finding]:
        return [item for item in self.findings if item.severity == "WARNING"]

    def add(self, line: int, rule: str, severity: Severity, message: str) -> None:
        self.findings.append(Finding(self.path, line, rule, severity, message))
