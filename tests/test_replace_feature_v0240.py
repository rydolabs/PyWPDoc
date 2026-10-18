from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from pywpdoc import Document, DocumentValueError
from pywpdoc.features.replace import replace_text

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


def _make_replace_doc(kind: str):
    doc = Document.new(kind)
    doc.add_paragraph("body needle")

    split = doc.add_paragraph("")
    split.clear()
    first = split.add_run("split nee")
    second = split.add_run("dle end")
    first.bold = True
    second.italic = True

    table = doc.add_table(1, 1)
    table.cell(0, 0).text = "table needle"
    doc.sections[0].header.text = "header needle"
    return doc, split


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_replace_text_uses_same_feature_api_for_both_backends(kind: str) -> None:
    doc, split = _make_replace_doc(kind)

    changed = doc.replace_text("needle", "value")
    assert changed == 4
    assert "split value end" == split.text
    assert "value" in doc.tables[0].cell(0, 0).text
    assert "value" in doc.sections[0].header.text


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_replace_text_crosses_run_boundaries_and_preserves_surviving_format(kind: str) -> None:
    doc = Document.new(kind)
    paragraph = doc.add_paragraph("")
    paragraph.clear()
    first = paragraph.add_run("AA nee")
    first.bold = True
    second = paragraph.add_run("dle ZZ")
    second.italic = True

    assert doc.replace_text("needle", "X", everywhere=False) == 1
    assert paragraph.text == "AA X ZZ"
    assert first.text == "AA X"
    assert second.text == " ZZ"
    assert first.bold is True
    assert second.italic is True


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_replace_text_handles_multiple_matches_in_one_source(kind: str) -> None:
    doc = Document.new(kind)
    paragraph = doc.add_paragraph("needle / needle / needle")

    assert doc.replace_text("needle", "X", everywhere=False, count=2) == 2
    assert paragraph.text == "X / X / needle"


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_replace_text_case_limit_and_body_scope_are_feature_owned(kind: str) -> None:
    doc = Document.new(kind)
    doc.add_paragraph("Needle needle NEEDLE")
    table = doc.add_table(1, 1)
    table.cell(0, 0).text = "needle"

    assert doc.replace_text(
        "needle", "X", everywhere=False, case_sensitive=False, count=2
    ) == 2
    assert doc.paragraphs[-1].text == "X X NEEDLE"
    assert table.cell(0, 0).text == "needle"


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_replace_text_rejects_empty_search(kind: str) -> None:
    doc = Document.new(kind)
    with pytest.raises(DocumentValueError) as excinfo:
        doc.replace_text("", "X")
    assert excinfo.value.code == "replace-query-empty"


def test_replace_function_can_target_backend_directly() -> None:
    doc = Document.new("hwpx")
    paragraph = doc.add_paragraph("backend needle")
    assert replace_text(doc.backend, "needle", "X", everywhere=False) == 1
    assert paragraph.text == "backend X"


def test_replace_does_not_depend_on_find_feature() -> None:
    source = (ROOT / "src/pywpdoc/features/replace/api.py").read_text(encoding="utf-8")
    assert "features.find" not in source
    assert "from ..find" not in source
    assert "from pywpdoc.features.find" not in source


def test_replace_noop_preserves_v0215_hwpx_golden(tmp_path: Path) -> None:
    source = ROOT / MANIFEST["source_fixture"]
    doc = Document.open(source)
    assert doc.replace_text("__NOT_PRESENT__", "X") == 0
    out = tmp_path / "noop.hwpx"
    doc.save(out)
    assert _zip_hashes(out) == MANIFEST["hwpx_package_parts"]


def test_replace_noop_preserves_docx_package_parts(tmp_path: Path) -> None:
    source = ROOT / MANIFEST["source_fixture"]
    selected = set(MANIFEST["docx_selected_parts"])

    baseline = Document.rebuild(source, format="docx", preserve_layout=True)
    before = tmp_path / "before.docx"
    baseline.save(before)

    changed = Document.rebuild(source, format="docx", preserve_layout=True)
    assert changed.replace_text("__NOT_PRESENT__", "X") == 0
    after = tmp_path / "after.docx"
    changed.save(after)

    assert _zip_hashes(after, selected) == _zip_hashes(before, selected)
    assert _zip_hashes(after, selected) == MANIFEST["docx_selected_parts"]


def test_replace_hwpx_hyperlink_boundary_uses_generic_writable_text_capability() -> None:
    doc = Document.new("hwpx")
    paragraph = doc.add_paragraph("Hello ")
    paragraph.add_hyperlink("https://example.com", "world")
    paragraph.add_run("!")

    assert doc.replace_text("ello world", "i there", everywhere=False) == 1
    assert paragraph.text == "Hi there!"
    assert len(paragraph.hyperlinks) == 1
    assert paragraph.hyperlinks[0].url == "https://example.com"
    assert paragraph.hyperlinks[0].text == ""


def test_replace_real_hwpx_changes_only_section_content_part(tmp_path: Path) -> None:
    source = ROOT / MANIFEST["source_fixture"]
    before = _zip_hashes(source)

    doc = Document.open(source)
    assert doc.replace_text("쓰담", "플로깅", count=1) == 1
    out = tmp_path / "replaced.hwpx"
    doc.save(out)

    after = _zip_hashes(out)
    changed = {name for name in before if before[name] != after[name]}
    assert changed == {"Contents/section0.xml"}
    reopened = Document.open(out)
    assert reopened.find("플로깅", count=1)


def test_replace_real_docx_keeps_unrelated_selected_parts_stable(tmp_path: Path) -> None:
    source = ROOT / MANIFEST["source_fixture"]
    selected = set(MANIFEST["docx_selected_parts"])

    doc = Document.rebuild(source, format="docx", preserve_layout=True)
    before = tmp_path / "before.docx"
    doc.save(before)

    assert doc.replace_text("쓰담", "플로깅", count=1) == 1
    after = tmp_path / "after.docx"
    doc.save(after)

    before_hashes = _zip_hashes(before, selected)
    after_hashes = _zip_hashes(after, selected)
    changed = {name for name in selected if before_hashes[name] != after_hashes[name]}
    assert changed == {"word/document.xml"}
    reopened = Document.open(after)
    assert reopened.find("플로깅", count=1)
