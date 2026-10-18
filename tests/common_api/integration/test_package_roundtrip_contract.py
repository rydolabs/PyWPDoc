"""ZIP/XML, media and relationships: observable package invariants."""
from __future__ import annotations
import zipfile
from lxml import etree
import pytest


@pytest.mark.common_api
@pytest.mark.parametrize("seed", ["plain", "table", "formatted", "mixed"])
def test_saved_archive_xml_is_parseable(document, save_reopen, common_format, seed):
    if seed in ("plain", "mixed"):
        document.add_paragraph("저장할 텍스트")
    if seed in ("table", "mixed"):
        document.add_table(2, 1).cell(1, 0).text = "셀"
    if seed == "formatted":
        document.add_paragraph().add_run("bold").bold = True
    _, path = save_reopen(document)
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        assert all(not name.startswith("/") and ".." not in name.split("/") for name in archive.namelist())
        names = archive.namelist()
        assert any(name.endswith(".xml") for name in names)
        for name in names:
            if name.endswith((".xml", ".rels", ".hpf", ".rdf")):
                etree.fromstring(archive.read(name))
        if common_format == "docx":
            assert "word/document.xml" in names
            assert "[Content_Types].xml" in names
        else:
            assert "mimetype" in names


@pytest.mark.common_api
def test_save_then_edit_then_save_again(document, tmp_path, common_format):
    document.add_paragraph("stage1")
    one = tmp_path / ("one." + common_format)
    two = tmp_path / ("two." + common_format)
    document.save(one)
    from pywpdoc import Document
    reopened = Document.open(one)
    reopened.add_paragraph("stage2")
    reopened.save(two)
    assert [p.text for p in Document.open(one).paragraphs] == ["stage1"]
    assert [p.text for p in Document.open(two).paragraphs] == ["stage1", "stage2"]


@pytest.mark.common_api
def test_original_input_unchanged_when_editing_open_copy(document, tmp_path, common_format):
    from pywpdoc import Document
    original = tmp_path / ("original." + common_format)
    changed = tmp_path / ("changed." + common_format)
    document.add_paragraph("BEFORE")
    document.save(original)
    original_bytes = original.read_bytes()
    opened = Document.open(original)
    assert opened.replace_text("BEFORE", "AFTER") == 1
    opened.save(changed)
    assert original.read_bytes() == original_bytes
    assert Document.open(changed).paragraphs[0].text == "AFTER"
