"""Typer CLI. Each subcommand is a thin wrapper around the stage functions in `dstoolkit.pipeline`,
so the step-by-step commands and `run` share exactly the same logic."""
from __future__ import annotations

import functools
import json
from pathlib import Path

import typer

from ..cleaning.rules import CleaningLog
from ..config import PipelineConfig
from ..pipeline import clean_stage, collect_stage, run_pipeline, validate_stage
from ..reporting import html_report, pdf_report
from ..utils import io as io_utils
from ..validation.rules import Issue, ValidationResult

app = typer.Typer(help="dstoolkit: collect, clean, validate, and report on tabular data.")


def _friendly_errors(func):
    """Turn expected failures (bad paths, bad config, network/DB errors) into a one-line
    message + exit code 1, instead of a raw Python traceback."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except typer.Exit:
            raise
        except Exception as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=1) from None

    return wrapper


@app.command()
@_friendly_errors
def collect(
    config: Path = typer.Argument(..., help="Path to the pipeline YAML config."),
    output: Path = typer.Option(..., "-o", "--output", help="Where to write the collected data."),
) -> None:
    """Collect raw data from the source described in CONFIG."""
    cfg = PipelineConfig.from_yaml(config)
    df = collect_stage(cfg)
    io_utils.write_dataframe(df, output)
    typer.echo(f"Collected {len(df)} rows -> {output}")


@app.command()
@_friendly_errors
def clean(
    input: Path = typer.Argument(..., help="Path to the collected data (parquet/csv)."),
    config: Path = typer.Argument(..., help="Path to the pipeline YAML config."),
    output: Path = typer.Option(..., "-o", "--output", help="Where to write the cleaned data."),
) -> None:
    """Clean INPUT using the cleaning options in CONFIG."""
    cfg = PipelineConfig.from_yaml(config)
    df = io_utils.read_dataframe(input)
    cleaned, log = clean_stage(df, cfg)
    io_utils.write_dataframe(cleaned, output)
    for action in log.as_text():
        typer.echo(f"  - {action}")
    typer.echo(f"Cleaned {len(cleaned)} rows -> {output}")


@app.command()
@_friendly_errors
def validate(
    input: Path = typer.Argument(..., help="Path to the cleaned data (parquet/csv)."),
    config: Path = typer.Argument(..., help="Path to the pipeline YAML config."),
    output: Path | None = typer.Option(None, "-o", "--output", help="Optional path to write results as JSON"),
) -> None:
    """Validate INPUT against the rules in CONFIG."""
    cfg = PipelineConfig.from_yaml(config)
    df = io_utils.read_dataframe(input)
    result = validate_stage(df, cfg)
    payload = {
        "passed": result.passed,
        "rules_evaluated": result.rules_evaluated,
        "issues": [issue.__dict__ for issue in result.issues],
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    typer.echo(json.dumps(payload, indent=2))
    if not result.passed:
        raise typer.Exit(code=1)


@app.command()
@_friendly_errors
def report(
    input: Path = typer.Argument(..., help="Path to the cleaned data (parquet/csv)."),
    config: Path = typer.Argument(..., help="Path to the pipeline YAML config."),
    validation: Path | None = typer.Option(None, "--validation", help="Prior `validate -o` JSON output"),
    output: Path = typer.Option(..., "-o", "--output", help="Where to write the report (.html or .pdf)."),
) -> None:
    """Render a report for INPUT, reusing a prior VALIDATION result if given."""
    cfg = PipelineConfig.from_yaml(config)
    df = io_utils.read_dataframe(input)
    cleaning_log = CleaningLog()

    if validation:
        data = json.loads(validation.read_text(encoding="utf-8"))
        result = ValidationResult(
            issues=[Issue(**issue) for issue in data.get("issues", [])],
            rules_evaluated=data.get("rules_evaluated", 0),
        )
    else:
        result = validate_stage(df, cfg)

    html = html_report.render(df, cleaning_log, result, title=cfg.report.title)
    if output.suffix.lower() == ".pdf":
        pdf_report.save(html, output)
    else:
        html_report.save(html, output)
    typer.echo(f"Report written to {output}")


@app.command()
@_friendly_errors
def run(config: Path = typer.Argument(..., help="Path to the pipeline YAML config.")) -> None:
    """Run the full pipeline (collect -> clean -> validate -> report) from CONFIG."""
    cfg = PipelineConfig.from_yaml(config)
    result = run_pipeline(cfg)
    for action in result.cleaning_log.as_text():
        typer.echo(f"  - {action}")
    n_issues = len(result.validation_result.issues)
    status = "PASSED" if result.validation_result.passed else f"{n_issues} ISSUE(S)"
    typer.echo(f"Validation: {status}")
    for fmt, path in result.report_paths.items():
        typer.echo(f"Report ({fmt}): {path}")


@app.command()
@_friendly_errors
def serve(
    host: str = typer.Option("127.0.0.1", help="Host to bind to."),
    port: int = typer.Option(8000, help="Port to bind to."),
) -> None:
    """Launch the web app (upload/clean/validate/report through the browser)."""
    import uvicorn

    typer.echo(f"Serving dstoolkit at http://{host}:{port}")
    uvicorn.run("dstoolkit.webapi.app:app", host=host, port=port)


if __name__ == "__main__":
    app()
