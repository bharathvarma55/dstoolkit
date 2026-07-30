"""Collect a DataFrame from a local file (CSV, Excel, JSON, or Parquet)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .base import CollectionResult

_READERS = {
    ".csv": pd.read_csv,
    ".tsv": lambda p, **kw: pd.read_csv(p, sep="\t", **kw),
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
