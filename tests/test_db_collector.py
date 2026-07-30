import pandas as pd
from sqlalchemy import create_engine

from dstoolkit.collectors import db_collector


def test_collect_from_sqlite(tmp_path):
    db_path = tmp_path / "test.db"
    conn_str = f"sqlite:///{db_path}"

    engine = create_engine(conn_str)
    pd.DataFrame({"a": [1, 2, 3]}).to_sql("t", engine, index=False)
    engine.dispose()

    result = db_collector.collect(conn_str, "SELECT * FROM t")
    assert result.row_count == 3
    assert list(result.df.columns) == ["a"]
    assert result.source_type == "db"
