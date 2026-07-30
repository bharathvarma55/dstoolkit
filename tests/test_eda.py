import pandas as pd

from dstoolkit.reporting.eda import compute_profile


def test_compute_profile_numeric_and_categorical():
    df = pd.DataFrame({"num": [1, 2, 3, None], "cat": ["x", "y", "x", "x"]})
    profile = compute_profile(df)
    assert profile.row_count == 4
    assert profile.col_count == 2

    num_col = next(c for c in profile.columns if c.name == "num")
    assert num_col.null == 1
    assert "mean" in num_col.stats

    cat_col = next(c for c in profile.columns if c.name == "cat")
    assert cat_col.top_values[0][0] == "x"
