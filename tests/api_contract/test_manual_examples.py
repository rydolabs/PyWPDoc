"""Run examples shipped with the online docs in both formats."""
import importlib.util
from pathlib import Path
import pytest
from pywpdoc import Document

ROOT = Path(__file__).resolve().parents[2]


def _load(name):
    spec = importlib.util.spec_from_file_location(f"manual_{name}", ROOT / "examples" / "manual" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_quickstart_creates_two_editable_files(tmp_path):
    paths = _load("quickstart").run(tmp_path)
    assert {p.suffix for p in paths} == {".docx", ".hwpx"}
    for path in paths:
        doc = Document.open(path)
        assert doc.paragraphs
        assert doc.tables[0].cell(1, 1).text == "12"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
@pytest.mark.parametrize("name", ["search_replace", "template", "pictures", "compare", "sections"])
def test_documented_example_runs(fmt, name, tmp_path):
    path = _load(name).run(fmt, tmp_path)
    assert path.exists() and path.stat().st_size > 0
    assert Document.open(path).format == fmt
