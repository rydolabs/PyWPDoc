"""v0.30 structural table-row capability shared by DOCX and HWPX backends."""
from __future__ import annotations

from base64 import b64decode
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from lxml import etree

from pywpdoc import Document, DocumentUnsupportedError, DocumentValueError
from pywpdoc._engine import Mm, WD_ALIGN_VERTICAL

PNG_1PX = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZQmcAAAAASUVORK5CYII="
)
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HC = "http://www.hancom.co.kr/hwpml/2011/core"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_clone_insert_remove_row_roundtrip_is_non_destructive(fmt: str, tmp_path: Path):
    doc = Document.new(fmt)
    table = doc.add_table(2, 2, style="Table Grid")
    table.cell(0, 0).text = "A"
    table.cell(0, 1).text = "B"
    table.cell(1, 0).text = "C"
    table.cell(1, 1).text = "D"

    token = table.clone_row(0)
    inserted = table.insert_row(1, token)
    assert [cell.text for cell in inserted.cells] == ["A", "B"]
    inserted.cells[0].text = "X"
    assert table.cell(0, 0).text == "A"
    assert table.cell(1, 0).text == "X"

    table.remove_row(2)
    assert len(table.rows) == 2
    out = tmp_path / f"row-structure.{fmt}"
    doc.save(out)
    reopened = Document.open(out)
    rows = reopened.tables[0].rows
    assert [[cell.text for cell in row.cells] for row in rows] == [["A", "B"], ["X", "B"]]


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_row_clone_preserves_height_horizontal_merge_and_nested_table(fmt: str, tmp_path: Path):
    doc = Document.new(fmt)
    table = doc.add_table(2, 3, style="Table Grid")
    row = table.rows[0]
    row.height = Mm(18)
    merged = table.cell(0, 0).merge(table.cell(0, 1))
    merged.text = "merged"
    table.cell(0, 2).vertical_alignment = WD_ALIGN_VERTICAL.BOTTOM
    nested = table.cell(0, 2).add_table(1, 2, style="Table Grid")
    nested.cell(0, 0).text = "N1"
    nested.cell(0, 1).text = "N2"

    inserted = table.insert_row(1, table.clone_row(0))
    assert abs(inserted.height.mm - 18.0) <= 0.05
    assert inserted.cells[0].text == "merged"
    # Logical merged cells repeat the same anchor in both backends.
    assert inserted.cells[1].text == "merged"
    assert inserted.cells[2].vertical_alignment == WD_ALIGN_VERTICAL.BOTTOM
    assert len(inserted.cells[2].tables) == 1
    assert inserted.cells[2].tables[0].cell(0, 1).text == "N2"

    out = tmp_path / f"row-merged-nested.{fmt}"
    doc.save(out)
    reopened = Document.open(out)
    cloned = reopened.tables[0].rows[1]
    assert abs(cloned.height.mm - 18.0) <= 0.05
    assert cloned.cells[0].text == "merged"
    assert cloned.cells[1].text == "merged"
    assert cloned.cells[2].tables[0].cell(0, 0).text == "N1"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_row_clone_preserves_picture_reference_with_fresh_object_identity(fmt: str, tmp_path: Path):
    doc = Document.new(fmt)
    table = doc.add_table(2, 1, style="Table Grid")
    if fmt == "docx":
        paragraph = table.cell(0, 0).paragraphs[0].native
        paragraph.add_run().add_picture(BytesIO(PNG_1PX))
    else:
        from pywpdoc._engine.authoring import add_binary_image
        binary_id = add_binary_image(doc.native, PNG_1PX, "png")
        table.cell(0, 0).paragraphs[0].native.add_picture(
            binary_id, width=7200, height=7200,
        )

    table.insert_row(1, table.clone_row(0))
    out = tmp_path / f"row-picture.{fmt}"
    doc.save(out)

    with ZipFile(out) as zf:
        if fmt == "docx":
            root = etree.fromstring(zf.read("word/document.xml"))
            ns = {"wp": WP, "a": A, "r": R}
            ids = root.xpath(".//wp:docPr/@id", namespaces=ns)
            embeds = root.xpath(".//a:blip/@r:embed", namespaces=ns)
            assert len(ids) == 2 and len(set(ids)) == 2
            assert len(embeds) == 2 and embeds[0] == embeds[1]
        else:
            root = etree.fromstring(zf.read("Contents/section0.xml"))
            ns = {"hp": HP, "hc": HC}
            ids = root.xpath(".//hp:pic/@id", namespaces=ns)
            instids = root.xpath(".//hp:pic/@instid", namespaces=ns)
            binary_refs = root.xpath(".//hc:img/@binaryItemIDRef", namespaces=ns)
            assert len(ids) == 2 and len(set(ids)) == 2
            assert ids == instids
            assert len(binary_refs) == 2 and binary_refs[0] == binary_refs[1]

    # Public reopen is part of the release safety contract.
    reopened = Document.open(out)
    assert len(reopened.tables[0].rows) == 3


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_row_clone_fails_closed_for_vertical_merge(fmt: str):
    doc = Document.new(fmt)
    table = doc.add_table(2, 2, style="Table Grid")
    table.cell(0, 0).merge(table.cell(1, 0)).text = "vertical"
    with pytest.raises(DocumentUnsupportedError) as excinfo:
        table.clone_row(0)
    assert excinfo.value.code == "table-row-vertical-merge-unsupported"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_row_token_is_scoped_to_originating_document(fmt: str):
    left = Document.new(fmt)
    right = Document.new(fmt)
    left_table = left.add_table(2, 1, style="Table Grid")
    right_table = right.add_table(2, 1, style="Table Grid")
    token = left_table.clone_row(0)
    with pytest.raises(DocumentValueError) as excinfo:
        right_table.insert_row(1, token)
    assert excinfo.value.code == "table-row-token-invalid"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_remove_last_table_row_is_rejected(fmt: str):
    doc = Document.new(fmt)
    table = doc.add_table(1, 1, style="Table Grid")
    with pytest.raises(DocumentValueError) as excinfo:
        table.remove_row(0)
    assert excinfo.value.code == "table-row-last-remove"
