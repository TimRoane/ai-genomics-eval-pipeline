import inspect
from pathlib import Path

from genomics_eval.cli import dashboard


def test_dashboard_command_default_detail_paths():
    params = inspect.signature(dashboard).parameters

    assert params["scores"].default.default == Path("data/results/scores.parquet")
    assert params["regression"].default.default == Path("data/results/regression_report.json")
    assert params["outputs"].default.default == Path("data/results/ai_outputs.jsonl")
    assert params["cases"].default.default == Path("data/raw/input_cases.jsonl")
    assert params["annotations"].default.default == Path("data/processed/annotated_variants.parquet")
