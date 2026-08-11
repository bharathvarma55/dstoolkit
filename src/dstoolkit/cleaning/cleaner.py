"""Cleaning stage: dedupe -> dtype coercion -> missing values -> string normalization ->
outlier capping. Every action taken is recorded in a `CleaningLog` for the report."""
from __future__ import annotations

import pandas as pd

from ..config import CleaningConfig
from .rules import CleaningLog


def clean(df: pd.DataFrame, config: CleaningConfig) -> tuple[pd.DataFrame, CleaningLog]:
    log = CleaningLog()
    df = df.copy()

    if config.dedupe:
        df = _dedupe(df, log)

    df = _coerce_dtypes(df, log)
    df = _handle_missing(df, config, log)

    if config.string_normalize:
        df = _normalize_strings(df, log)

    if config.outlier_strategy == "iqr_cap":
        df = _cap_outliers(df, config, log)

    return df, log


def _dedupe(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    if removed:
        log.add(f"Removed {removed} duplicate row(s)", removed)
    return df


def _coerce_dtypes(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """Convert text columns to numeric only when it loses no information (no new nulls)."""
    for col in df.columns:
        series = df[col]
        if (
            pd.api.types.is_numeric_dtype(series)
            or pd.api.types.is_bool_dtype(series)
            or pd.api.types.is_datetime64_any_dtype(series)
        ):
            continue
        converted = pd.to_numeric(df[col], errors="coerce")
        original_na = df[col].isna()
        newly_na = converted.isna() & ~original_na
        if newly_na.sum() == 0 and converted.notna().sum() > 0:
            df[col] = converted
            log.add(f"Converted column '{col}' from text to numeric")
    return df


def _fill_column(
    df: pd.DataFrame, col: str, strategy: str, config: CleaningConfig, log: CleaningLog
) -> pd.DataFrame:
    n_missing = df[col].isna().sum()
    if n_missing == 0:
        return df

    if strategy == "drop":
        before = len(df)
        df = df.dropna(subset=[col])
        removed = before - len(df)
        if removed:
            log.add(f"Dropped {removed} row(s) with missing '{col}'", removed)
        return df

    if strategy == "mean" and pd.api.types.is_numeric_dtype(df[col]):
        value = df[col].mean()
    elif strategy == "median" and pd.api.types.is_numeric_dtype(df[col]):
        value = df[col].median()
    elif strategy == "constant":
        value = config.missing_value_constant
    else:
        # "mode", or a numeric strategy requested on a non-numeric column
        mode = df[col].mode()
        value = mode.iloc[0] if not mode.empty else None

    if value is None or (isinstance(value, float) and pd.isna(value)):
        log.add(
            f"Could not fill {n_missing} missing value(s) in '{col}' with {strategy} "
            f"(no value could be computed, e.g. the column may be entirely empty) — left as-is",
            n_missing,
        )
        return df

    df[col] = df[col].fillna(value)
    log.add(f"Filled {n_missing} missing value(s) in '{col}' with {strategy} ({value!r})", n_missing)
    return df


def _handle_missing(df: pd.DataFrame, config: CleaningConfig, log: CleaningLog) -> pd.DataFrame:
    override_cols = set(config.missing_value_overrides)

    for col, strategy in config.missing_value_overrides.items():
        if col in df.columns:
            df = _fill_column(df, col, strategy, config, log)

    remaining_cols = [c for c in df.columns if c not in override_cols and df[c].isna().any()]

    if config.missing_value_strategy == "drop":
        if remaining_cols:
            before = len(df)
            df = df.dropna(subset=remaining_cols)
            removed = before - len(df)
            if removed:
                log.add(f"Dropped {removed} row(s) with missing values", removed)
    else:
        for col in remaining_cols:
            df = _fill_column(df, col, config.missing_value_strategy, config, log)

    return df


def _normalize_strings(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """Trim leading/trailing whitespace from string columns."""
    affected = []
    for col in df.columns:
        series = df[col]
        if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
            continue
        stripped = series.apply(lambda v: v.strip() if isinstance(v, str) else v)
        if not stripped.equals(series):
            affected.append(col)
        df[col] = stripped
    if affected:
        log.add(f"Trimmed whitespace in column(s): {', '.join(affected)}")
    return df


def _cap_outliers(df: pd.DataFrame, config: CleaningConfig, log: CleaningLog) -> pd.DataFrame:
    """Clip numeric outliers to the IQR fence [Q1 - 1.5*IQR, Q3 + 1.5*IQR]."""
    columns = config.outlier_columns or list(df.select_dtypes(include="number").columns)
    for col in columns:
        if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
            continue
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_affected = int(((df[col] < lower) | (df[col] > upper)).sum())
        if n_affected:
            df[col] = df[col].clip(lower=lower, upper=upper)
            log.add(f"Capped {n_affected} outlier(s) in '{col}' to [{lower:.3g}, {upper:.3g}]", n_affected)
    return df
