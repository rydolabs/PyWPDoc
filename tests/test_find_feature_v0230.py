from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from pywpdoc import Document, DocumentValueError
from pywpdoc.core.text import TextMap
from pywpdoc.features.find import FindMatch, find

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "tests/baseline/v0215_manifest.json").read_text(encoding="utf-8"))


def _zip_hashes(path: Path, selected: set[str] | None = None) -> dict[str, str]:
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        if selected is not None:
            names &= selected
        return {
            name: hashlib.sha256(zf.read(name)).hexdigest()
            for name in sorted(names)
        }


def _make_search_doc(kind: str):
    doc = Document.new(kind)
    doc.add_paragraph("body needle")

    split = doc.add_paragraph("")
    split.clear()
    split.add_run("split nee")
    split.add_run("dle end")

    table = doc.add_table(1, 1)
    table.cell(0, 0).text = "table needle"

    doc.sections[0].header.text = "header needle"
    return doc, split


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_find_uses_same_feature_api_for_both_backends(kind: str) -> None:
    doc, split = _make_search_doc(kind)

    matches = doc.find("needle")
    assert len(matches) == 4
    assert all(isinstance(match, FindMatch) for match in matches)
    assert any(match.paragraph.text == split.text for match in matches)

    body_only = doc.find("needle", everywhere=False)
    assert len(body_only) == 2


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_find_matches_across_run_boundaries(kind: str) -> None:
    doc = Document.new(kind)
    paragraph = doc.add_paragraph("")
    paragraph.clear()
    paragraph.add_run("{{cus")
    paragraph.add_run("tomer.name}}")

    matches = doc.find("{{customer.name}}", everywhere=False)
    assert len(matches) == 1
    match = matches[0]
    assert match.start == 0
    assert match.end == len("{{customer.name}}")
    assert match.text == "{{customer.name}}"

    text_map = TextMap.from_paragraph(match.paragraph)
    touched = text_map.sources_for(match.start, match.end)
    assert len(touched) == 2


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_find_case_and_limit_are_feature_owned(kind: str) -> None:
    doc = Document.new(kind)
    doc.add_paragraph("Needle needle NEEDLE")

    assert len(doc.find("needle", everywhere=False)) == 1
    assert len(doc.find("needle", everywhere=False, case_sensitive=False)) == 3
    assert len(doc.find("needle", everywhere=False, case_sensitive=False, count=2)) == 2
    assert doc.find("needle", everywhere=False, count=0) == []


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_find_rejects_empty_query(kind: str) -> None:
    doc = Document.new(kind)
    with pytest.raises(DocumentValueError) as excinfo:
        doc.find("")
    assert excinfo.value.code == "find-query-empty"


def test_find_function_can_target_backend_directly() -> None:
    doc = Document.new("hwpx")
    doc.add_paragraph("backend needle")
    matches = find(doc.backend, "needle", everywhere=False)
    assert len(matches) == 1


def test_find_is_read_only_for_v0215_hwpx_golden(tmp_path: Path) -> None:
    source = ROOT / MANIFEST["source_fixture"]
    doc = Document.open(source)
    assert doc.find("쓰담")
    out = tmp_path / "searched.hwpx"
    doc.save(out)
    assert _zip_hashes(out) == MANIFEST["hwpx_package_parts"]


def test_find_is_read_only_for_docx_package_parts(tmp_path: Path) -> None:
    source = ROOT / MANIFEST["source_fixture"]
    selected = set(MANIFEST["docx_selected_parts"])

    baseline = Document.rebuild(source, format="docx", preserve_layout=True)
    before = tmp_path / "before.docx"
    baseline.save(before)

    searched = Document.rebuild(source, format="docx", preserve_layout=True)
    assert searched.find("쓰담")
    after = tmp_path / "after.docx"
    searched.save(after)

    assert _zip_hashes(after, selected) == _zip_hashes(before, selected)
    assert _zip_hashes(after, selected) == MANIFEST["docx_selected_parts"]
