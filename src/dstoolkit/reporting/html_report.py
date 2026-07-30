"""Render the self-contained HTML report from a cleaned DataFrame plus the logs produced by
the cleaning and validation stages."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..cleaning.rules import CleaningLog
from ..validation.rules import ValidationResult
from . import charts
from .eda import compute_profile

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def render(
    df: pd.DataFrame,
    cleaning_log: CleaningLog,
    validation_result: ValidationResult,
    title: str = "Data Science Report",
) -> str:
    profile = compute_profile(df)
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html.jinja")
    return template.render(
        title=title,
        profile=profile,
        cleaning_actions=cleaning_log.as_text(),
        validation=validation_result,
        missingness_chart=charts.missingness_chart(df),
        histograms=charts.histogram_charts(df),
        correlation_chart=charts.correlation_heatmap(df),
    )


def save(html: str, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
