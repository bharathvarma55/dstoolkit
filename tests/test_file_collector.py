from pathlib import Path

import pytest

from dstoolkit.collectors import file_collector

DATA_DIR = Path(__file__).parent / "data"


def test_collect_csv(tmp_path):
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("a,b\n1,2\n3,4\n")
    result = file_collector.collect(csv_path)
    assert result.row_count == 2
    assert result.col_count == 2
    assert list(result.df.columns) == ["a", "b"]


def test_collect_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        file_collector.collect(tmp_path / "missing.csv")


def test_collect_unsupported_format(tmp_path):
    bad = tmp_path / "data.txt"
    bad.write_text("hello")
    with pytest.raises(ValueError):
        file_collector.collect(bad)


def test_collect_messy_sample():
    result = file_collector.collect(DATA_DIR / "sample.csv")
    assert result.row_count == 10
    assert result.col_count == 5
    assert result.df.duplicated().sum() == 1


def test_collect_csv_falls_back_from_utf8_on_non_utf8_bytes(tmp_path):
    csv_path = tmp_path / "windows1252.csv"
    # cp1252-only bytes (e.g. the '£' pound sign) are not valid UTF-8 and would raise
    # UnicodeDecodeError under plain pd.read_csv(path).
    csv_path.write_bytes("name,price\nWidget,£9.99\n".encode("cp1252"))
    result = file_collector.collect(csv_path)
    assert result.row_count == 1
    assert result.df["price"].iloc[0] == "£9.99"


def test_collect_csv_respects_explicit_encoding(tmp_path):
    csv_path = tmp_path / "explicit.csv"
    csv_path.write_bytes("name,price\nWidget,£9.99\n".encode("cp1252"))
    result = file_collector.collect(csv_path, encoding="cp1252")
    assert result.df["price"].iloc[0] == "£9.99"
