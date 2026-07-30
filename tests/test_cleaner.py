import pandas as pd

from dstoolkit.cleaning.cleaner import clean
from dstoolkit.config import CleaningConfig


def test_dedupe_and_missing(messy_df):
    config = CleaningConfig(missing_value_strategy="median")
    cleaned, log = clean(messy_df, config)
    assert len(cleaned) == 3
    assert cleaned["age"].isna().sum() == 0
    assert any("duplicate" in a.lower() for a in log.as_text())


def test_string_normalize(messy_df):
    config = CleaningConfig(dedupe=False, missing_value_strategy="drop", string_normalize=True)
    cleaned, _ = clean(messy_df, config)
    assert cleaned["name"].iloc[0] == "Alice"
    assert cleaned["name"].iloc[1] == "Bob"


def test_outlier_capping():
    df = pd.DataFrame({"x": [1, 2, 3, 4, 1000]})
    config = CleaningConfig(dedupe=False, missing_value_strategy="drop", outlier_strategy="iqr_cap")
    cleaned, log = clean(df, config)
    assert cleaned["x"].max() < 1000
    assert any("outlier" in a.lower() for a in log.as_text())


def test_dtype_coercion_is_lossless():
    df = pd.DataFrame({"x": ["1", "2", "3"]})
    config = CleaningConfig(dedupe=False, missing_value_strategy="drop", outlier_strategy="none")
    cleaned, log = clean(df, config)
    assert pd.api.types.is_numeric_dtype(cleaned["x"])
    assert any("numeric" in a.lower() for a in log.as_text())


def test_all_null_column_is_left_alone_and_logged():
    df = pd.DataFrame({"a": [None, None, None], "b": [1, 2, 3]})
    config = CleaningConfig(dedupe=False, missing_value_strategy="mean")
    cleaned, log = clean(df, config)
    assert cleaned["a"].isna().all()
    assert any("could not fill" in a.lower() for a in log.as_text())


def test_empty_dataframe_does_not_crash():
    df = pd.DataFrame({"a": pd.Series(dtype="float64"), "b": pd.Series(dtype="object")})
    cleaned, log = clean(df, CleaningConfig())
    assert len(cleaned) == 0


def test_single_row_outlier_capping_does_not_crash():
    df = pd.DataFrame({"x": [42]})
    config = CleaningConfig(dedupe=False, missing_value_strategy="drop", outlier_strategy="iqr_cap")
    cleaned, _ = clean(df, config)
    assert cleaned["x"].iloc[0] == 42
