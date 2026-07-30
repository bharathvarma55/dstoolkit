import pandas as pd

from dstoolkit.config import ValidationRuleConfig
from dstoolkit.validation.validator import validate


def test_not_null_rule():
    df = pd.DataFrame({"a": [1, None, 3]})
    rules = [ValidationRuleConfig(type="not_null", column="a")]
    result = validate(df, rules)
    assert not result.passed
    assert result.issues[0].rule == "not_null"


def test_unique_rule():
    df = pd.DataFrame({"a": [1, 1, 2]})
    rules = [ValidationRuleConfig(type="unique", column="a")]
    result = validate(df, rules)
    assert not result.passed


def test_range_rule():
    df = pd.DataFrame({"a": [1, 5, 10]})
    rules = [ValidationRuleConfig(type="range", column="a", params={"min": 0, "max": 8})]
    result = validate(df, rules)
    assert not result.passed
    assert result.issues[0].affected_rows == 1


def test_allowed_values_rule():
    df = pd.DataFrame({"a": ["x", "y", "z"]})
    rules = [ValidationRuleConfig(type="allowed_values", column="a", params={"values": ["x", "y"]})]
    result = validate(df, rules)
    assert not result.passed
    assert result.issues[0].affected_rows == 1


def test_range_rule_on_non_numeric_column_does_not_crash():
    df = pd.DataFrame({"a": ["x", "y", "z"]})
    rules = [ValidationRuleConfig(type="range", column="a", params={"min": 0, "max": 10})]
    result = validate(df, rules)
    assert not result.passed
    assert "non-numeric" in result.issues[0].message


def test_malformed_regex_does_not_crash_the_whole_run():
    df = pd.DataFrame({"a": ["x", "y"]})
    rules = [
        ValidationRuleConfig(type="regex", column="a", params={"pattern": "["}),  # invalid regex
        ValidationRuleConfig(type="unique", column="a"),
    ]
    result = validate(df, rules)
    assert result.rules_evaluated == 2
    assert len(result.issues) == 1
    assert result.issues[0].rule == "regex"


def test_passing_rules():
    df = pd.DataFrame({"a": [1, 2, 3]})
    rules = [
        ValidationRuleConfig(type="not_null", column="a"),
        ValidationRuleConfig(type="unique", column="a"),
    ]
    result = validate(df, rules)
    assert result.passed
    assert result.rules_passed == 2
