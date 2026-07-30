"""Data structures produced by the validation stage."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Issue:
    rule: str
    column: str
    message: str
    affected_rows: int = 0
    severity: str = "error"


@dataclass
class ValidationResult:
    issues: list[Issue] = field(default_factory=list)
    rules_evaluated: int = 0

    @property
    def passed(self) -> bool:
        return len(self.issues) == 0

    @property
    def rules_passed(self) -> int:
        return self.rules_evaluated - len(self.issues)
