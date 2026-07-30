"""Shared collector interface.

`CollectionResult` is the common return type every collector produces. `Collector` is the
Protocol future collectors (db_collector, api_collector, web_collector) implement so the rest
of the pipeline never needs to know where a DataFrame came from.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd


@dataclass
class CollectionResult:
    df: pd.DataFrame
    source_type: str
    source_name: str

    @property
    def row_count(self) -> int:
        return len(self.df)

    @property
    def col_count(self) -> int:
        return len(self.df.columns)


class Collector(Protocol):
    def collect(self, **kwargs: Any) -> CollectionResult: ...
