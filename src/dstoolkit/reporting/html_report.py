"""Render the self-contained HTML report from a cleaned DataFrame plus the logs produced by
the cleaning and validation stages."""
from __future__ import annotations

from pathlib import Path
from typing import Any

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
    chart_specs: list[dict[str, Any]] | None = None,
) -> str:
    """`chart_specs` is a list of `{"type": ..., "params": {...}}`, dispatched through
    `charts.render_chart`. `None` (the default, e.g. plain `dstk run`) falls back to
    `charts.default_chart_specs` — an explicit `[]` means "no charts", not "use the default"."""
    profile = compute_profile(df)
    specs = chart_specs if chart_specs is not None else charts.default_chart_specs(df)
    rendered_charts = [charts.render_chart(df, spec["type"], spec.get("params", {})) for spec in specs]

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
        charts=rendered_charts,
    )


def save(html: str, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
