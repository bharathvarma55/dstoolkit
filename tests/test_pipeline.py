import pandas as pd
import yaml

from dstoolkit.config import PipelineConfig
from dstoolkit.pipeline import run_pipeline


def test_run_pipeline_end_to_end(tmp_path):
    csv_path = tmp_path / "data.csv"
    pd.DataFrame(
        {
            "id": [1, 2, 2, 3],
            "name": [" A", "B ", "B ", "C"],
            "age": [10, 20, 20, None],
        }
    ).to_csv(csv_path, index=False)

    config = {
        "source": {"type": "file", "path": str(csv_path)},
        "cleaning": {"missing_value_strategy": "median"},
        "validation": [{"type": "not_null", "column": "age"}],
        "report": {"output_dir": str(tmp_path / "reports"), "title": "Test"},
    }
    config_path = tmp_path / "pipeline.yaml"
    config_path.write_text(yaml.dump(config), encoding="utf-8")

    cfg = PipelineConfig.from_yaml(config_path)
    result = run_pipeline(cfg)

    assert result.validation_result.passed
    assert (tmp_path / "reports" / "report.html").exists()
    assert len(result.df) == 3
