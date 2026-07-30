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
