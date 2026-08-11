"""FastAPI app: serves the static frontend and mounts the /api routes."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routes import router

_STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="dstoolkit")
app.include_router(router)
app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
