"""Render charts as base64-embedded PNGs so the HTML report has no external asset dependencies."""
from __future__ import annotations

import base64
from io import BytesIO

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def _fig_to_data_uri(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def missingness_chart(df: pd.DataFrame) -> str | None:
    null_counts = df.isna().sum()
    null_counts = null_counts[null_counts > 0]
    if null_counts.empty:
        return None
    fig, ax = plt.subplots(figsize=(6, max(2, 0.4 * len(null_counts))))
    null_counts.sort_values().plot.barh(ax=ax, color="#c0392b")
    ax.set_xlabel("Missing value count")
    ax.set_title("Missing values by column")
    return _fig_to_data_uri(fig)


def histogram_charts(df: pd.DataFrame, max_columns: int = 6) -> list[tuple[str, str]]:
    numeric_cols = list(df.select_dtypes(include="number").columns)[:max_columns]
    charts = []
    for col in numeric_cols:
        fig, ax = plt.subplots(figsize=(5, 3))
        df[col].dropna().plot.hist(ax=ax, bins=20, color="#2980b9")
        ax.set_title(f"Distribution of {col}")
        charts.append((col, _fig_to_data_uri(fig)))
    return charts


def correlation_heatmap(df: pd.DataFrame) -> str | None:
    numeric = df.select_dtypes(include="number")
    if numeric.shape[1] < 2:
        return None
    corr = numeric.corr()
    fig, ax = plt.subplots(figsize=(1 + 0.6 * len(corr), 1 + 0.6 * len(corr)))
    im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(corr.columns)))
    ax.set_yticklabels(corr.columns)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title("Correlation heatmap")
    return _fig_to_data_uri(fig)
