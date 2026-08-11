import pandas as pd

from dstoolkit.reporting import charts


def _sample_df():
    return pd.DataFrame(
        {
            "age": [25, 30, 35, 40, None],
            "salary": [50000, 60000, 70000, 80000, 90000],
            "city": ["NY", "NY", "LA", "LA", "SF"],
        }
    )


def test_render_chart_histogram():
    result = charts.render_chart(_sample_df(), "histogram", {"column": "age"})
    assert "data_uri" in result
    assert result["data_uri"].startswith("data:image/png;base64,")


def test_render_chart_bar():
    result = charts.render_chart(_sample_df(), "bar", {"column": "city"})
    assert "data_uri" in result


def test_render_chart_box():
    result = charts.render_chart(_sample_df(), "box", {"column": "salary"})
    assert "data_uri" in result


def test_render_chart_scatter():
    result = charts.render_chart(_sample_df(), "scatter", {"x": "age", "y": "salary"})
    assert "data_uri" in result


def test_render_chart_line():
    result = charts.render_chart(_sample_df(), "line", {"column": "salary"})
    assert "data_uri" in result


def test_render_chart_pie():
    result = charts.render_chart(_sample_df(), "pie", {"column": "city"})
    assert "data_uri" in result


def test_render_chart_correlation():
    result = charts.render_chart(_sample_df(), "correlation", {})
    assert "data_uri" in result


def test_render_chart_missingness():
    result = charts.render_chart(_sample_df(), "missingness", {})
    assert "data_uri" in result


def test_render_chart_missing_column_is_an_error_not_a_crash():
    result = charts.render_chart(_sample_df(), "histogram", {"column": "nope"})
    assert "error" in result
    assert "not found" in result["error"]


def test_render_chart_non_numeric_column_is_an_error_not_a_crash():
    df = pd.DataFrame({"city": ["NY", "LA", "SF"]})
    result = charts.render_chart(df, "histogram", {"column": "city"})
    assert "error" in result


def test_render_chart_unknown_type_is_an_error_not_a_crash():
    result = charts.render_chart(_sample_df(), "not_a_real_type", {})
    assert "error" in result
    assert "Unknown chart type" in result["error"]


def test_render_chart_correlation_needs_two_numeric_columns():
    df = pd.DataFrame({"age": [1, 2, 3]})
    result = charts.render_chart(df, "correlation", {})
    assert "error" in result


def test_default_chart_specs():
    specs = charts.default_chart_specs(_sample_df())
    types = [s["type"] for s in specs]
    assert "missingness" in types
    assert "histogram" in types
    assert "correlation" in types
