import pandas as pd

from dstoolkit.cleaning.rules import CleaningLog
from dstoolkit.reporting import html_report
from dstoolkit.validation.rules import Issue, ValidationResult


def test_render_contains_key_sections():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    log = CleaningLog()
    log.add("Removed 1 duplicate row")
    result = ValidationResult(issues=[Issue("not_null", "a", "boom", 1)], rules_evaluated=1)

    html = html_report.render(df, log, result, title="Test Report")

    assert "Test Report" in html
    assert "Removed 1 duplicate row" in html
    assert "boom" in html
    assert "Column Profiles" in html
