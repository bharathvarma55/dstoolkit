"""API routes for the web app. Every operation reuses the exact stage functions the CLI uses
(dstoolkit.collectors / cleaning.cleaner / validation.validator / reporting.*) — no pipeline
logic is duplicated here, only request/response glue."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..cleaning.cleaner import clean
from ..collectors import file_collector
from ..config import ChartConfig, CleaningConfig, ValidationRuleConfig
from ..reporting import html_report, pdf_report
from ..validation.validator import validate
from .state import SessionState, store

router = APIRouter(prefix="/api")


def _json_safe(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _preview(df: pd.DataFrame, limit: int = 20) -> dict[str, Any]:
    head = df.head(limit)
    rows = [[_json_safe(v) for v in row] for row in head.itertuples(index=False, name=None)]
    return {
        "columns": [str(c) for c in df.columns],
        "rows": rows,
        "row_count": len(df),
        "col_count": len(df.columns),
    }


def _get_session(session_id: str) -> SessionState:
    try:
        return store.get(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/upload")
async def upload(file: UploadFile) -> dict[str, Any]:
    suffix = Path(file.filename or "").suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        result = file_collector.collect(tmp_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    session_id = store.create(result.df, source_name=file.filename or "upload")
    return {"session_id": session_id, "preview": _preview(result.df)}


@router.get("/sessions/{session_id}/preview")
def get_preview(session_id: str) -> dict[str, Any]:
    session = _get_session(session_id)
    return {"preview": _preview(session.df)}


@router.get("/sessions/{session_id}/columns")
def get_columns(session_id: str) -> dict[str, Any]:
    """Column names plus whether each is numeric, so the frontend's chart builder can offer the
    right columns for each chart type (e.g. only numeric ones for a histogram)."""
    session = _get_session(session_id)
    columns = [
        {"name": str(col), "numeric": bool(pd.api.types.is_numeric_dtype(session.df[col]))}
        for col in session.df.columns
    ]
    return {"columns": columns}


@router.post("/sessions/{session_id}/clean")
def run_clean(session_id: str, config: CleaningConfig) -> dict[str, Any]:
    session = _get_session(session_id)
    cleaned, log = clean(session.df, config)
    session.df = cleaned
    session.cleaning_log = log
    return {"cleaning_log": log.as_text(), "preview": _preview(cleaned)}


class ValidateRequest(BaseModel):
    rules: list[ValidationRuleConfig]


@router.post("/sessions/{session_id}/validate")
def run_validate(session_id: str, body: ValidateRequest) -> dict[str, Any]:
    session = _get_session(session_id)
    result = validate(session.df, body.rules)
    session.validation_result = result
    return {
        "passed": result.passed,
        "rules_evaluated": result.rules_evaluated,
        "issues": [issue.__dict__ for issue in result.issues],
    }


class ReportRequest(BaseModel):
    title: str = "Data Science Report"
    charts: list[ChartConfig] = Field(default_factory=list)


@router.post("/sessions/{session_id}/report")
def run_report(session_id: str, body: ReportRequest) -> dict[str, Any]:
    session = _get_session(session_id)
    chart_specs = [c.model_dump() for c in body.charts]
    session.report_html = html_report.render(
        session.df,
        session.cleaning_log,
        session.validation_result,
        title=body.title,
        chart_specs=chart_specs,
    )
    return {"ready_formats": ["html", "pdf"]}


@router.get("/sessions/{session_id}/report/{fmt}")
def get_report(session_id: str, fmt: str, download: bool = False) -> Response:
    session = _get_session(session_id)
    if session.report_html is None:
        raise HTTPException(status_code=404, detail="No report generated yet for this session")

    disposition = "attachment" if download else "inline"
    if fmt == "html":
        return Response(
            content=session.report_html,
            media_type="text/html",
            headers={"Content-Disposition": f'{disposition}; filename="report.html"'},
        )
    if fmt == "pdf":
        pdf_bytes = pdf_report.render_bytes(session.report_html)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'{disposition}; filename="report.pdf"'},
        )
    raise HTTPException(status_code=400, detail=f"Unsupported format '{fmt}'")
