"""Collect a DataFrame by scraping a web page.

Two modes, chosen by which options are given:
- `selector` + `fields`: CSS selector for repeating row elements, and a sub-selector per field
  (BeautifulSoup), for pages that aren't a plain HTML table.
- otherwise: extract the `table_index`-th `<table>` element via `pandas.read_html`.
"""
from __future__ import annotations

from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .base import CollectionResult

# Many sites (e.g. Wikipedia) return 403 for requests' default User-Agent; a browser-like one
# avoids that without misrepresenting the request in any other way.
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def collect(
    url: str,
    selector: str | None = None,
    fields: dict[str, str] | None = None,
    table_index: int = 0,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
) -> CollectionResult:
    response = requests.get(url, timeout=timeout, headers={**_DEFAULT_HEADERS, **(headers or {})})
    response.raise_for_status()

    if selector and fields:
        soup = BeautifulSoup(response.text, "html.parser")
        rows = []
        for element in soup.select(selector):
            row = {}
            for field_name, sub_selector in fields.items():
                found = element.select_one(sub_selector)
                row[field_name] = found.get_text(strip=True) if found else None
            rows.append(row)
        df = pd.DataFrame(rows, columns=list(fields.keys()))
    else:
        tables = pd.read_html(StringIO(response.text))
        if not tables:
            raise ValueError(f"No <table> elements found at {url}")
        df = tables[table_index]

    return CollectionResult(df=df, source_type="web", source_name=url)
