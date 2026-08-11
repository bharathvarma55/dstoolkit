"""Collect a DataFrame from a local file (CSV, Excel, JSON, or Parquet)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .base import CollectionResult

# Tried in order until one decodes cleanly. utf-8-sig strips a BOM if present; cp1252 covers
# most files exported from Excel on Windows; latin-1 maps every byte to a codepoint so it never
# raises, guaranteeing this loop always terminates.
_CSV_ENCODING_FALLBACKS = ("utf-8", "utf-8-sig", "cp1252", "latin-1")


def _read_csv_robust(path: Path, **options: Any) -> pd.DataFrame:
    if "encoding" in options:
        return pd.read_csv(path, **options)
    last_error: UnicodeDecodeError | None = None
    for encoding in _CSV_ENCODING_FALLBACKS:
        try:
            return pd.read_csv(path, encoding=encoding, **options)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise last_error  # pragma: no cover - latin-1 above never raises


_READERS = {
    ".csv": _read_csv_robust,
    ".tsv": lambda p, **kw: _read_csv_robust(p, sep="\t", **kw),
    ".xlsx": pd.read_excel,
    ".xls": pd.read_excel,
    ".json": pd.read_json,
    ".parquet": pd.read_parquet,
}

_FORMAT_EXT = {
    "csv": ".csv",
    "excel": ".xlsx",
    "json": ".json",
    "parquet": ".parquet",
}


def collect(path: str | Path, format: str | None = None, **options: Any) -> CollectionResult:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")

    suffix = _FORMAT_EXT[format] if format else path.suffix.lower()
    reader = _READERS.get(suffix)
    if reader is None:
        supported = ", ".join(sorted(_READERS))
        raise ValueError(f"Unsupported file format '{suffix}' for {path}. Supported: {supported}")

    df = reader(path, **options)
    return CollectionResult(df=df, source_type="file", source_name=str(path))
