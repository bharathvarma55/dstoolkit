"""In-memory session store for the web API. Each session holds the working DataFrame plus the
logs produced by the cleaning/validation stages, keyed by a UUID handed back to the client.

Intentionally in-process only (no persistence, no expiry) — fine for this project's single-user,
local-tool scope. Must run under a single uvicorn worker: state living in a plain dict isn't
shared across worker processes.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import pandas as pd

from ..cleaning.rules import CleaningLog
from ..validation.rules import ValidationResult


@dataclass
class SessionState:
    df: pd.DataFrame
    source_name: str
    cleaning_log: CleaningLog = field(default_factory=CleaningLog)
    validation_result: ValidationResult = field(default_factory=ValidationResult)
    report_html: str | None = None


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def create(self, df: pd.DataFrame, source_name: str) -> str:
        session_id = uuid.uuid4().hex
        self._sessions[session_id] = SessionState(df=df, source_name=source_name)
        return session_id

    def get(self, session_id: str) -> SessionState:
        try:
            return self._sessions[session_id]
        except KeyError:
            raise KeyError(f"Unknown session '{session_id}' — upload a file first") from None


store = SessionStore()
