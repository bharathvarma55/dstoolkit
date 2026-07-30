from typer.testing import CliRunner

from dstoolkit.cli.main import app

runner = CliRunner()


def test_run_with_missing_config_file_is_a_friendly_error(tmp_path):
    result = runner.invoke(app, ["run", str(tmp_path / "does_not_exist.yaml")])
    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "Error:" in result.output


def test_run_with_invalid_config_is_a_friendly_error(tmp_path):
    config_path = tmp_path / "bad.yaml"
    config_path.write_text("source:\n  type: file\n", encoding="utf-8")  # missing required path
    result = runner.invoke(app, ["run", str(config_path)])
    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "Error:" in result.output
