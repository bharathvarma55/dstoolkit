"""Collect a DataFrame from a REST API's JSON response."""
from __future__ import annotations

from typing import Any

import pandas as pd
import requests

from .base import CollectionResult


def _extract(data: Any, json_path: str | None) -> Any:
    """Walk a dotted path (e.g. "data.items") into a parsed JSON payload."""
    if not json_path:
        return data
    for key in json_path.split("."):
        data = data[key]
    return data


def collect(
    url: str,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    json_path: str | None = None,
    timeout: float = 30.0,
) -> CollectionResult:
    response = requests.request(method, url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    data = _extract(response.json(), json_path)
    df = pd.json_normalize(data)
    return CollectionResult(df=df, source_type="api", source_name=url)
