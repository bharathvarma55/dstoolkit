"""Render the same HTML report to PDF via xhtml2pdf (pure Python, no system dependencies —
picked over WeasyPrint so this works identically on Windows/Mac/Linux with just `pip install`).

xhtml2pdf has weaker CSS support than a browser (no flexbox, limited layout), so the PDF is
laid out more simply than the HTML version, but carries the same content.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from xhtml2pdf import pisa


def render_bytes(html: str) -> bytes:
    buf = BytesIO()
    result = pisa.CreatePDF(html, dest=buf)
    if result.err:
        raise RuntimeError(f"Failed to render PDF ({result.err} error(s))")
    return buf.getvalue()


def save(html: str, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(render_bytes(html))
    return output_path
