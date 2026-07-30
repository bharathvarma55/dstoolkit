"""Data structures for recording what the cleaning stage did."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CleaningAction:
    description: str
    rows_affected: int = 0


@dataclass
class CleaningLog:
    actions: list[CleaningAction] = field(default_factory=list)

    def add(self, description: str, rows_affected: int = 0) -> None:
        self.actions.append(CleaningAction(description, rows_affected))

    def as_text(self) -> list[str]:
        return [a.description for a in self.actions]
