"""Validation stage: a dispatch table maps rule type -> checker function. Each checker
inspects the DataFrame and returns an `Issue` if the rule failed, or `None` if it passed."""
from __future__ import annotations

import re
from typing import Any, Callable

import pandas as pd

from ..config import ValidationRuleConfig
from .rules import Issue, ValidationResult

Checker = Callable[[pd.DataFrame, str, dict[str, Any]], "Issue | None"]


def _check_not_null(df: pd.DataFrame, column: str, params: dict[str, Any]) -> Issue | None:
    if column not in df.columns:
        return Issue("not_null", column, f"Column '{column}' not found")
    max_null_rate = params.get("max_null_rate", 0.0)
    n = len(df)
    n_null = int(df[column].isna().sum())
    rate = n_null / n if n else 0.0
    if rate > max_null_rate:
        return Issue(
            "not_null", column,
            f"{n_null} null value(s) ({rate:.1%}) exceed max allowed rate {max_null_rate:.1%}",
            n_null,
        )
    return None


def _check_unique(df: pd.DataFrame, column: str, params: dict[str, Any]) -> Issue | None:
    if column not in df.columns:
        return Issue("unique", column, f"Column '{column}' not found")
    dup_mask = df[column].duplicated(keep=False) & df[column].notna()
    n_dup = int(dup_mask.sum())
    if n_dup:
        return Issue("unique", column, f"{n_dup} duplicate value(s) found", n_dup)
    return None


def _check_dtype(df: pd.DataFrame, column: str, params: dict[str, Any]) -> Issue | None:
    if column not in df.columns:
        return Issue("dtype", column, f"Column '{column}' not found")
    expected = params.get("expected", "")
    kind_checks = {
        "numeric": pd.api.types.is_numeric_dtype,
        "string": lambda s: s.dtype == object,
        "datetime": pd.api.types.is_datetime64_any_dtype,
        "bool": pd.api.types.is_bool_dtype,
    }
    check = kind_checks.get(expected)
    ok = check(df[column]) if check else str(df[column].dtype) == expected
    if not ok:
        return Issue("dtype", column, f"Expected dtype '{expected}', got '{df[column].dtype}'")
    return None


def _check_range(df: pd.DataFrame, column: str, params: dict[str, Any]) -> Issue | None:
    if column not in df.columns:
        return Issue("range", column, f"Column '{column}' not found")
    series = df[column]
    if not pd.api.types.is_numeric_dtype(series):
        return Issue("range", column, f"Cannot apply a range rule to non-numeric column '{column}' (dtype {series.dtype})")
    min_v, max_v = params.get("min"), params.get("max")
    mask = pd.Series(False, index=series.index)
    if min_v is not None:
        mask |= series < min_v
    if max_v is not None:
        mask |= series > max_v
    n = int((mask & series.notna()).sum())
    if n:
        return Issue("range", column, f"{n} value(s) outside range [{min_v}, {max_v}]", n)
    return None


def _check_allowed_values(df: pd.DataFrame, column: str, params: dict[str, Any]) -> Issue | None:
    if column not in df.columns:
        return Issue("allowed_values", column, f"Column '{column}' not found")
    allowed = set(params.get("values", []))
    mask = ~df[column].isin(allowed) & df[column].notna()
    n = int(mask.sum())
    if n:
        return Issue("allowed_values", column, f"{n} value(s) not in allowed set {sorted(allowed)}", n)
    return None


def _check_regex(df: pd.DataFrame, column: str, params: dict[str, Any]) -> Issue | None:
    if column not in df.columns:
        return Issue("regex", column, f"Column '{column}' not found")
    pattern = re.compile(params.get("pattern", ""))
    non_null = df[column].notna()
    mismatched = df[column].apply(lambda v: isinstance(v, str) and not pattern.match(v))
    n = int((mismatched & non_null).sum())
    if n:
        return Issue("regex", column, f"{n} value(s) do not match pattern '{pattern.pattern}'", n)
    return None


_CHECKERS: dict[str, Checker] = {
    "not_null": _check_not_null,
    "unique": _check_unique,
    "dtype": _check_dtype,
    "range": _check_range,
    "allowed_values": _check_allowed_values,
    "regex": _check_regex,
}


def validate(df: pd.DataFrame, rules: list[ValidationRuleConfig]) -> ValidationResult:
    result = ValidationResult(rules_evaluated=len(rules))
    for rule in rules:
        checker = _CHECKERS.get(rule.type)
        if checker is None:
            continue
        try:
            issue = checker(df, rule.column, rule.params)
        except Exception as exc:  # a single malformed rule shouldn't crash the whole run
            issue = Issue(rule.type, rule.column, f"Rule could not be evaluated: {exc}")
        if issue is not None:
            result.issues.append(issue)
    return result
