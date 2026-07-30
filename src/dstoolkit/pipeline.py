"""Orchestrates the four pipeline stages. Each stage function is also used independently by
the CLI's step-by-step commands, so there is exactly one implementation of each stage."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .cleaning.cleaner import clean
from .cleaning.rules import CleaningLog
from .collectors import api_collector, db_collector, file_collector, web_collector
from .config import PipelineConfig
from .reporting import html_report, pdf_report
from .validation.rules import ValidationResult
from .validation.validator import validate


@dataclass
class PipelineResult:
    df: pd.DataFrame
    cleaning_log: CleaningLog
    validation_result: ValidationResult
    report_paths: dict[str, Path]


def collect_stage(config: PipelineConfig) -> pd.DataFrame:
    source = config.source
    if source.type == "file":
        result = file_collector.collect(source.path, format=source.format, **source.options)
    elif source.type == "db":
        result = db_collector.collect(source.connection_string, source.query)
    elif source.type == "api":
        result = api_collector.collect(
            source.url,
            method=source.method,
            params=source.params,
            headers=source.headers,
            json_path=source.json_path,
        )
    elif source.type == "web":
        result = web_collector.collect(
            source.url,
            selector=source.selector,
            fields=source.fields,
            table_index=source.table_index,
            headers=source.headers,
        )
    else:
        raise ValueError(f"Unsupported source type: {source.type}")
    return result.df


def clean_stage(df: pd.DataFrame, config: PipelineConfig) -> tuple[pd.DataFrame, CleaningLog]:
    return clean(df, config.cleaning)


def validate_stage(df: pd.DataFrame, config: PipelineConfig) -> ValidationResult:
    return validate(df, config.validation)


def report_stage(
    df: pd.DataFrame,
    cleaning_log: CleaningLog,
    validation_result: ValidationResult,
    config: PipelineConfig,
) -> dict[str, Path]:
    html = html_report.render(df, cleaning_log, validation_result, title=config.report.title)
    output_dir = Path(config.report.output_dir)
    paths: dict[str, Path] = {}
    if "html" in config.report.formats:
        paths["html"] = html_report.save(html, output_dir / "report.html")
    if "pdf" in config.report.formats:
        paths["pdf"] = pdf_report.save(html, output_dir / "report.pdf")
    return paths


def run_pipeline(config: PipelineConfig) -> PipelineResult:
    df = collect_stage(config)
    df, cleaning_log = clean_stage(df, config)
    validation_result = validate_stage(df, config)
    report_paths = report_stage(df, cleaning_log, validation_result, config)
    return PipelineResult(df, cleaning_log, validation_result, report_paths)
