"""Batch gate orchestration must continue after independently failing gates."""
from pathlib import Path
import pytest

from tests.quality.native_batch_suite import create_suite
from tests.quality.run_batch_checks import run_all


def test_project_batch_continues_native_analysis_after_pytest_execution_error(tmp_path: Path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    create_suite(source / "qa_native_batch_v0400")

    def failed_subprocess(*args, **kwargs):
        raise OSError("simulated pytest launcher problem")

    monkeypatch.setattr("quality.run_batch_checks.subprocess.run", failed_subprocess)
    result = run_all(source, tmp_path / "logs")
    assert result["gates"]["python_tests"]["status"] == "ERROR"
    assert result["native_batch"]["status"] == "NOT_SUBMITTED"
    assert result["native_batch"]["counts"] == {"SKIP": 10}
    issues = (tmp_path / "logs" / "issues.log").read_text(encoding="utf-8")
    assert "[PYTEST ERROR]" in issues
    assert "[NATIVE SKIP] T01_INSERT" in issues
