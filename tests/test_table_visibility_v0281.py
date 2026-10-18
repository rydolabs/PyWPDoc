from __future__ import annotations

from pathlib import Path
import shutil
from zipfile import ZipFile

import pytest
from lxml import etree

from pywpdoc import Document
from tests.quality.docx_table_visibility import (
    VisualToolUnavailable,
    has_visible_table_grid,
    render_first_page_to_pgm,
)


def _make_section_template(kind: str) -> Document:
    doc = Document.new(kind)
    doc.add_paragraph("고객: {{customer.name}}")
    doc.add_paragraph("{{#items}}[{{name}}={{qty}}] {{/items}}{{^items}}항목 없음{{/items}}")
    table = doc.add_table(2, 2, style="Table Grid")
    table.cell(0, 0).text = "항목"
    table.cell(0, 1).text = "값"
    table.cell(1, 0).text = "비고"
    table.cell(1, 1).text = "{{#show_note}}{{note}}{{/show_note}}"
    return doc


def _render_data() -> dict:
    return {
        "customer": {"name": "홍길동"},
        "items": [{"name": "A", "qty": 2}, {"name": "B", "qty": 3}],
        "show_note": True,
        "note": "확인",
    }


def test_docx_explicit_table_grid_survives_template_render_and_reopen(tmp_path: Path) -> None:
    doc = _make_section_template("docx")
    assert doc.tables[0].native.style.name == "Table Grid"
    doc.render_template(_render_data(), sections=True)
    out = tmp_path / "visible-grid.docx"
    doc.save(out)

    reopened = Document.open(out)
    assert reopened.tables[0].native.style.name == "Table Grid"
    assert reopened.tables[0].cell(1, 1).text == "확인"

    with ZipFile(out) as package:
        root = etree.fromstring(package.read("word/document.xml"))
    values = root.xpath(
        "//*[local-name()='tblStyle']/@*[local-name()='val']"
    )
    assert "TableGrid" in values


def test_hwpx_explicit_table_grid_has_visible_solid_border_fill(tmp_path: Path) -> None:
    doc = _make_section_template("hwpx")
    doc.render_template(_render_data(), sections=True)
    out = tmp_path / "visible-grid.hwpx"
    doc.save(out)

    with ZipFile(out) as package:
        section = etree.fromstring(package.read("Contents/section0.xml"))
        header = etree.fromstring(package.read("Contents/header.xml"))

    table_refs = section.xpath(
        "//*[local-name()='tbl']/@borderFillIDRef"
    )
    assert table_refs
    border_id = table_refs[0]
    fills = header.xpath(
        f"//*[local-name()='borderFill' and @id='{border_id}']"
    )
    assert len(fills) == 1
    fill = fills[0]
    for side in ("leftBorder", "rightBorder", "topBorder", "bottomBorder"):
        nodes = fill.xpath(f"./*[local-name()='{side}']")
        assert len(nodes) == 1
        assert nodes[0].get("type") == "SOLID"
        assert nodes[0].get("color") == "#000000"


def test_docx_rendered_table_grid_is_visibly_bordered(tmp_path: Path) -> None:
    if shutil.which("soffice") is None or shutil.which("pdftoppm") is None:
        pytest.skip("LibreOffice/pdftoppm visual QA tools unavailable")

    doc = _make_section_template("docx")
    doc.render_template(_render_data(), sections=True)
    out = tmp_path / "visible-grid.docx"
    doc.save(out)

    try:
        pgm = render_first_page_to_pgm(out, tmp_path / "render")
    except VisualToolUnavailable as exc:
        pytest.skip(str(exc))
    assert has_visible_table_grid(pgm)


def test_default_table_style_semantics_remain_backend_owned() -> None:
    """The v0.28.1 QA fix must not silently change add_table(style=None)."""
    docx = Document.new("docx")
    hwpx = Document.new("hwpx")
    docx_table = docx.add_table(1, 1)
    hwpx_table = hwpx.add_table(1, 1)

    assert docx_table.native.style.name == "Normal Table"
    # HWPX owns its own native default borderFill semantics; do not normalize it
    # to the DOCX default as part of this sample/QA correction.
    assert hwpx_table.style != "Table Grid"
