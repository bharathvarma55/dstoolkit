"""Collect a DataFrame by running a SQL query against any SQLAlchemy-supported database."""
from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import create_engine

from .base import CollectionResult


def collect(connection_string: str, query: str, **read_sql_kwargs: Any) -> CollectionResult:
    engine = create_engine(connection_string)
    try:
        df = pd.read_sql(query, engine, **read_sql_kwargs)
    finally:
        engine.dispose()
    return CollectionResult(df=df, source_type="db", source_name=connection_string)
