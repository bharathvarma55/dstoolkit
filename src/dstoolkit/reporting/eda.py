"""Compute dataset- and column-level statistics used by the HTML report."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    non_null: int
    null: int
    null_rate: float
    unique: int
    stats: dict[str, Any] = field(default_factory=dict)
    top_values: list[tuple[Any, int]] = field(default_factory=list)


@dataclass
class DatasetProfile:
    row_count: int
    col_count: int
    duplicate_rows: int
    memory_usage_kb: float
    columns: list[ColumnProfile] = field(default_factory=list)


def compute_profile(df: pd.DataFrame) -> DatasetProfile:
    columns = []
    for col in df.columns:
        series = df[col]
        non_null = int(series.notna().sum())
        null = int(series.isna().sum())
        profile = ColumnProfile(
            name=col,
            dtype=str(series.dtype),
            non_null=non_null,
            null=null,
            null_rate=(null / len(df)) if len(df) else 0.0,
            unique=int(series.nunique(dropna=True)),
        )
        if pd.api.types.is_numeric_dtype(series):
            profile.stats = {
                "min": series.min(),
                "max": series.max(),
                "mean": series.mean(),
                "median": series.median(),
                "std": series.std(),
            }
        else:
            top = series.value_counts(dropna=True).head(5)
            profile.top_values = list(top.items())
        columns.append(profile)

    return DatasetProfile(
        row_count=len(df),
        col_count=len(df.columns),
        duplicate_rows=int(df.duplicated().sum()),
        memory_usage_kb=float(df.memory_usage(deep=True).sum() / 1024),
        columns=columns,
    )
