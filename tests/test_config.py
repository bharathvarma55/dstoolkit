import pytest
from pydantic import ValidationError

from dstoolkit.config import CleaningConfig, SourceConfig


def test_constant_strategy_requires_constant_value():
    with pytest.raises(ValidationError):
        CleaningConfig(missing_value_strategy="constant")


def test_constant_strategy_with_value_is_fine():
    config = CleaningConfig(missing_value_strategy="constant", missing_value_constant=0)
    assert config.missing_value_constant == 0


def test_constant_override_requires_constant_value():
    with pytest.raises(ValidationError):
        CleaningConfig(missing_value_overrides={"city": "constant"})


def test_file_source_requires_path():
    with pytest.raises(ValidationError):
        SourceConfig(type="file")


def test_db_source_requires_connection_and_query():
    with pytest.raises(ValidationError):
        SourceConfig(type="db", connection_string="sqlite:///x.db")


def test_api_source_requires_url():
    with pytest.raises(ValidationError):
        SourceConfig(type="api")
