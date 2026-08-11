"""Chart rendering. Each chart type is a small function `(df, params) -> (title, data_uri)`,
registered in `_CHART_RENDERERS` and dispatched by `render_chart` — the same
type-string-to-function pattern used by `validation/validator.py`'s `_CHECKERS`. Charts render
as base64-embedded PNGs so the HTML report has no external asset dependencies.

A renderer raises `ValueError` for "can't plot this" cases (wrong dtype, no data); `render_chart`
catches that and returns an error entry instead of failing the whole report, the same way a
single malformed validation rule doesn't crash `validate()`.
"""
from __future__ import annotations

import base64
from collections.abc import Callable
from io import BytesIO
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

_COLOR = "#2980b9"
_DANGER_COLOR = "#c0392b"


def _fig_to_data_uri(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _require_column(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found")
    return df[column]


def _numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    series = _require_column(df, column)
    numeric = series if pd.api.types.is_numeric_dtype(series) else pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() == 0:
        raise ValueError(f"Column '{column}' has no numeric data to plot")
    return numeric


def render_histogram(df: pd.DataFrame, params: dict[str, Any]) -> tuple[str, str]:
    column = params["column"]
    series = _numeric_series(df, column).dropna()
    fig, ax = plt.subplots(figsize=(6, 4))
    series.plot.hist(ax=ax, bins=20, color=_COLOR)
    ax.set_title(f"Distribution of {column}")
    ax.set_xlabel(column)
    return f"Histogram — {column}", _fig_to_data_uri(fig)


def render_bar(df: pd.DataFrame, params: dict[str, Any]) -> tuple[str, str]:
    column = params["column"]
    counts = _require_column(df, column).value_counts(dropna=True).head(10)
    if counts.empty:
        raise ValueError(f"Column '{column}' has no values to plot")
    fig, ax = plt.subplots(figsize=(6, 4))
    counts.sort_values().plot.barh(ax=ax, color=_COLOR)
    ax.set_title(f"Top values in {column}")
    return f"Bar chart — {column}", _fig_to_data_uri(fig)


def render_box(df: pd.DataFrame, params: dict[str, Any]) -> tuple[str, str]:
    column = params["column"]
    series = _numeric_series(df, column).dropna()
    fig, ax = plt.subplots(figsize=(4, 5))
    # Set the tick label via set_xticklabels rather than boxplot's labels/tick_labels kwarg —
    # that kwarg was renamed between matplotlib versions (labels -> tick_labels), this isn't.
    ax.boxplot(series, patch_artist=True, boxprops={"facecolor": _COLOR, "alpha": 0.5})
    ax.set_xticks([1])
    ax.set_xticklabels([column])
    ax.set_title(f"Box plot — {column}")
    return f"Box plot — {column}", _fig_to_data_uri(fig)


def render_scatter(df: pd.DataFrame, params: dict[str, Any]) -> tuple[str, str]:
    x_col, y_col = params["x"], params["y"]
    x, y = _numeric_series(df, x_col), _numeric_series(df, y_col)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(x, y, alpha=0.6, color=_COLOR, edgecolors="none")
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(f"{y_col} vs {x_col}")
    return f"Scatter — {y_col} vs {x_col}", _fig_to_data_uri(fig)


def render_line(df: pd.DataFrame, params: dict[str, Any]) -> tuple[str, str]:
    column = params["column"]
    series = _numeric_series(df, column)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(series.to_numpy(), color=_COLOR)
    ax.set_title(f"{column} by row order")
    ax.set_xlabel("Row")
    ax.set_ylabel(column)
    return f"Line chart — {column}", _fig_to_data_uri(fig)


def render_pie(df: pd.DataFrame, params: dict[str, Any]) -> tuple[str, str]:
    column = params["column"]
    counts = _require_column(df, column).value_counts(dropna=True).head(8)
    if counts.empty:
        raise ValueError(f"Column '{column}' has no values to plot")
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(counts.to_numpy(), labels=counts.index.astype(str), autopct="%1.0f%%")
    ax.set_title(f"{column} composition")
    return f"Pie chart — {column}", _fig_to_data_uri(fig)


def render_correlation(df: pd.DataFrame, params: dict[str, Any]) -> tuple[str, str]:
    numeric = df.select_dtypes(include="number")
    if numeric.shape[1] < 2:
        raise ValueError("Need at least two numeric columns for a correlation heatmap")
    corr = numeric.corr()
    fig, ax = plt.subplots(figsize=(1 + 0.6 * len(corr), 1 + 0.6 * len(corr)))
    im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(corr.columns)))
    ax.set_yticklabels(corr.columns)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title("Correlation heatmap")
    return "Correlation heatmap", _fig_to_data_uri(fig)


def render_missingness(df: pd.DataFrame, params: dict[str, Any]) -> tuple[str, str]:
    null_counts = df.isna().sum()
    null_counts = null_counts[null_counts > 0]
    if null_counts.empty:
        raise ValueError("No missing values to plot")
    fig, ax = plt.subplots(figsize=(6, max(2, 0.4 * len(null_counts))))
    null_counts.sort_values().plot.barh(ax=ax, color=_DANGER_COLOR)
    ax.set_xlabel("Missing value count")
    ax.set_title("Missing values by column")
    return "Missing values by column", _fig_to_data_uri(fig)


_CHART_RENDERERS: dict[str, Callable[[pd.DataFrame, dict[str, Any]], tuple[str, str]]] = {
    "histogram": render_histogram,
    "bar": render_bar,
    "box": render_box,
    "scatter": render_scatter,
    "line": render_line,
    "pie": render_pie,
    "correlation": render_correlation,
    "missingness": render_missingness,
}


def render_chart(df: pd.DataFrame, chart_type: str, params: dict[str, Any]) -> dict[str, str]:
    """Render one chart spec. Returns `{type, title, data_uri}` on success or
    `{type, title, error}` if the chart couldn't be produced — never raises."""
    renderer = _CHART_RENDERERS.get(chart_type)
    if renderer is None:
        return {"type": chart_type, "title": chart_type, "error": f"Unknown chart type '{chart_type}'"}
    try:
        title, data_uri = renderer(df, params)
        return {"type": chart_type, "title": title, "data_uri": data_uri}
    except Exception as exc:
        return {"type": chart_type, "title": chart_type, "error": str(exc)}


def default_chart_specs(df: pd.DataFrame, max_histograms: int = 6) -> list[dict[str, Any]]:
    """The automatic chart set used when nothing more specific was requested (e.g. `dstk run`
    with no `report.charts` in the config): missingness, a histogram per numeric column, and a
    correlation heatmap — this is exactly what the report produced before charts became
    selectable."""
    specs: list[dict[str, Any]] = [{"type": "missingness", "params": {}}]
    numeric_cols = list(df.select_dtypes(include="number").columns)
    specs += [{"type": "histogram", "params": {"column": c}} for c in numeric_cols[:max_histograms]]
    if len(numeric_cols) >= 2:
        specs.append({"type": "correlation", "params": {}})
    return specs
