import pandas as pd
import pytest


@pytest.fixture
def messy_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 3],
            "name": [" Alice", "Bob ", "Charlie", "Charlie"],
            "age": [34, 29, None, None],
            "salary": [55000, 62000, 58000, 58000],
        }
    )
