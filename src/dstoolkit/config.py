"""Pydantic configuration models for the dstoolkit pipeline.

A `PipelineConfig` is normally loaded from a YAML file (see `examples/pipeline.yaml`) and
describes the four stages of the pipeline: source, cleaning, validation, and report.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class SourceConfig(BaseModel):
    """Where to collect data from. Fields are grouped by `type`; only the fields relevant to
    the chosen type need to be set. See collectors/{file,db,api,web}_collector.py."""

    type: Literal["file", "db", "api", "web"] = "file"

    # type == "file"
    path: str | None = None
    format: Literal["csv", "excel", "json", "parquet"] | None = None
    options: dict[str, Any] = Field(default_factory=dict)

    # type == "db"
    connection_string: str | None = None
    query: str | None = None

    # type == "api"
    url: str | None = None
    method: str = "GET"
    params: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    json_path: str | None = None

    # type == "web"
    selector: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    table_index: int = 0

    @model_validator(mode="after")
    def _check_required_fields(self) -> SourceConfig:
        if self.type == "file" and not self.path:
            raise ValueError("source.path is required when source.type is 'file'")
        if self.type == "db" and not (self.connection_string and self.query):
            raise ValueError(
                "source.connection_string and source.query are required when source.type is 'db'"
            )
        if self.type in ("api", "web") and not self.url:
            raise ValueError(f"source.url is required when source.type is '{self.type}'")
        return self


class CleaningConfig(BaseModel):
    """Options controlling the cleaning stage. Applied in a fixed order: dedupe -> dtype
    coercion -> missing values -> string normalization -> outlier capping."""

    dedupe: bool = True
    missing_value_strategy: Literal["drop", "mean", "median", "mode", "constant"] = "drop"
    missing_value_constant: Any = None
    missing_value_overrides: dict[str, str] = Field(default_factory=dict)
    string_normalize: bool = True
    outlier_strategy: Literal["iqr_cap", "none"] = "iqr_cap"
    outlier_columns: list[str] | None = None

    @model_validator(mode="after")
    def _check_constant_value_set(self) -> CleaningConfig:
        uses_constant = (
            self.missing_value_strategy == "constant"
            or "constant" in self.missing_value_overrides.values()
        )
        if uses_constant and self.missing_value_constant is None:
            raise ValueError(
                "cleaning.missing_value_constant must be set when using the 'constant' fill strategy"
            )
        return self


class ValidationRuleConfig(BaseModel):
    """A single declarative validation rule, dispatched by `type` in validation/validator.py."""

    type: Literal["not_null", "unique", "dtype", "range", "allowed_values", "regex"]
    column: str
    params: dict[str, Any] = Field(default_factory=dict)


class ReportConfig(BaseModel):
    output_dir: str = "reports"
    formats: list[Literal["html", "pdf"]] = Field(default_factory=lambda: ["html"])
    title: str = "Data Science Report"


class PipelineConfig(BaseModel):
    source: SourceConfig
    cleaning: CleaningConfig = Field(default_factory=CleaningConfig)
    validation: list[ValidationRuleConfig] = Field(default_factory=list)
    report: ReportConfig = Field(default_factory=ReportConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> PipelineConfig:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.model_validate(data)
