"""Public, generated-data, black-box behavior matrix for DOCX and HWPX.

This suite supplements the historical native format regressions.  Its cases
require no third-party/private document, and each test checks an observable
API contract rather than implementation-specific XML element counts.
"""
from __future__ import annotations

import re
import zipfile

import pytest

from pywpdoc import Document
from pywpdoc._engine.core.errors import DocumentUnsupportedError, DocumentValueError


FORMATS = ("docx", "hwpx")


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("sample", [
    "한글 English 2026", "emoji 😀 café", "tag <&> and quotes \"'", "Arabic العربية 中文",
])
def test_unicode_roundtrip_body_and_table(fmt, sample, tmp_path):
    document = Document.new(fmt)
    document.add_paragraph(sample)
    table = document.add_table(1, 1)
    table.cell(0, 0).text = sample
    path = tmp_path / ("unicode." + fmt)
    document.save(path)
    reopened = Document.open(path)
    assert sample in [paragraph.text for paragraph in reopened.paragraphs]
    assert reopened.tables[0].cell(0, 0).text == sample
    with zipfile.ZipFile(path) as package:
        assert package.testzip() is None


@pytest.mark.parametrize("fmt", FORMATS)
def test_search_and_preview_are_read_only(fmt, tmp_path):
    document = Document.new(fmt)
    document.add_paragraph("TOKEN before TOKEN")
    document.add_paragraph("TOKEN after")
    before = [paragraph.text for paragraph in document.paragraphs]
    assert len(document.find("TOKEN")) == 3
    _ = document.preview_replace("TOKEN", "DONE")
    assert [paragraph.text for paragraph in document.paragraphs] == before
    saved = tmp_path / ("preview." + fmt)
    document.save(saved)
    assert [paragraph.text for paragraph in Document.open(saved).paragraphs] == before


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("limit", [0, 1, 2, -1])
def test_literal_replacement_global_count(fmt, limit):
    document = Document.new(fmt)
    for _ in range(3):
        document.add_paragraph("old")
    assert document.replace_text("old", "new", count=limit) == (3 if limit < 0 else limit)
    expected = 3 if limit < 0 else limit
    assert [p.text for p in document.paragraphs].count("new") == expected


@pytest.mark.parametrize("fmt", FORMATS)
def test_literal_replacement_empty_query_preserves_document(fmt):
    document = Document.new(fmt)
    document.add_paragraph("Keep original")
    with pytest.raises(DocumentValueError) as error:
        document.replace_text("", "changed")
    assert error.value.code == "replace-query-empty"
    assert document.paragraphs[0].text == "Keep original"


@pytest.mark.parametrize("fmt", FORMATS)
def test_regex_invalid_capture_preserves_all_paragraphs(fmt):
    document = Document.new(fmt)
    for word in ("A01", "B02", "C03"):
        document.add_paragraph(word)
    before = [p.text for p in document.paragraphs]
    with pytest.raises(DocumentValueError) as error:
        document.replace_regex(r"([A-Z])(\d+)", r"\g<missing>")
    assert error.value.code == "regex-replacement-invalid"
    assert [p.text for p in document.paragraphs] == before


@pytest.mark.parametrize("fmt", FORMATS)
def test_regex_zero_width_preserves_all_paragraphs(fmt):
    document = Document.new(fmt)
    document.add_paragraph("alpha beta")
    with pytest.raises(DocumentUnsupportedError) as error:
        document.replace_regex(r"(?=alpha)", "bad")
    assert error.value.code == "regex-zero-width"
    assert document.paragraphs[0].text == "alpha beta"


@pytest.mark.parametrize("fmt", FORMATS)
def test_template_missing_late_paragraph_is_atomic(fmt):
    document = Document.new(fmt)
    document.add_paragraph("VALID {{key}}")
    document.add_paragraph("MISSING {{absent}}")
    original = [p.text for p in document.paragraphs]
    with pytest.raises(DocumentValueError) as error:
        document.render_template({"key": "yes"}, missing="error", everywhere=False)
    assert error.value.code == "template-value-missing"
    assert [p.text for p in document.paragraphs] == original


@pytest.mark.parametrize("fmt", FORMATS)
def test_template_missing_late_table_is_atomic(fmt):
    document = Document.new(fmt)
    document.add_paragraph("VALID {{key}}")
    document.add_table(1, 1).cell(0, 0).text = "MISSING {{absent}}"
    with pytest.raises(DocumentValueError) as error:
        document.render_template({"key": "yes"}, missing="error", everywhere=True)
    assert error.value.code == "template-value-missing"
    assert document.paragraphs[0].text == "VALID {{key}}"
    assert document.tables[0].cell(0, 0).text == "MISSING {{absent}}"


@pytest.mark.parametrize("fmt", FORMATS)
def test_compare_body_only_fails_for_table_cell_change_and_preserves_inputs(fmt):
    old, new = Document.new(fmt), Document.new(fmt)
    for doc in (old, new):
        doc.add_paragraph("same body")
        doc.add_table(1, 1).cell(0, 0).text = "first"
    new.tables[0].cell(0, 0).text = "second"
    with pytest.raises(DocumentUnsupportedError) as error:
        old.compare(new, everywhere=False)
    assert error.value.code == "compare-outside-scope-changes-unsupported"
    assert old.tables[0].cell(0, 0).text == "first"
    assert new.tables[0].cell(0, 0).text == "second"


@pytest.mark.parametrize("fmt", FORMATS)
def test_compare_body_only_allows_text_change_when_table_identical(fmt, tmp_path):
    old, new = Document.new(fmt), Document.new(fmt)
    for doc, text in ((old, "before"), (new, "after")):
        doc.add_paragraph(text)
        doc.add_table(1, 1).cell(0, 0).text = "unchanged"
    comparison = old.compare(new, everywhere=False)
    output = tmp_path / ("tracked." + fmt)
    comparison.save(output)
    with zipfile.ZipFile(output) as package:
        content = b"".join(package.read(n) for n in package.namelist() if n.endswith(".xml"))
    assert (b"<w:ins" if fmt == "docx" else b"insertBegin") in content
    assert old.paragraphs[0].text == "before"
    assert new.paragraphs[0].text == "after"


def test_docx_to_hwpx_rebuild_rejected_by_explicit_code(tmp_path):
    original = Document.new("docx")
    original.add_paragraph("must not be lost")
    path = tmp_path / "input.docx"
    original.save(path)
    with pytest.raises(DocumentUnsupportedError) as error:
        Document.rebuild(path, format="hwpx")
    assert error.value.code == "rebuild-docx-to-hwpx-unsupported"
    assert Document.open(path).paragraphs[0].text == "must not be lost"


def test_docx_same_format_rebuild_preserves_package_parts(tmp_path):
    document = Document.new("docx")
    document.add_paragraph("must remain")
    document.add_table(2, 2).cell(1, 1).text = "important table data"
    original = tmp_path / "original.docx"
    rebuilt = tmp_path / "rebuilt.docx"
    document.save(original)
    Document.rebuild(original, format="docx").save(rebuilt)
    with zipfile.ZipFile(original) as before, zipfile.ZipFile(rebuilt) as after:
        assert set(before.namelist()) == set(after.namelist())
        assert before.read("word/document.xml") == after.read("word/document.xml")
    reopened = Document.open(rebuilt)
    assert reopened.paragraphs[0].text == "must remain"
    assert reopened.tables[0].cell(1, 1).text == "important table data"


def test_hwpx_bulk_replace_synthetic_fixture_not_wallclock(tmp_path):
    doc = Document.new("hwpx")
    for i in range(400):
        doc.add_paragraph(f"[{i:04d}] old")
    assert doc.replace_text("old", "new") == 400
    out = tmp_path / "bulk.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    assert sum("new" in p.text for p in reopened.paragraphs) == 400
    assert all("old" not in p.text for p in reopened.paragraphs)
