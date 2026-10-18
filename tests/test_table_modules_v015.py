"""v0.15 table module isolation and backend-owned geometry gates."""
from __future__ import annotations

import ast
from pathlib import Path
from zipfile import ZipFile

import pytest
from lxml import etree

from pywpdoc._engine import WD_ALIGN_VERTICAL

ROOT = Path(__file__).resolve().parents[1] / "src" / "pywpdoc" / "_engine"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _backend_class(kind: str):
    if kind == "hwpx":
        from pywpdoc._engine.hwpx import Document
    else:
        from pywpdoc._engine.docx import Document
    return Document


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append("." * node.level + (node.module or ""))
    return names


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_table_and_geometry_modules_have_narrow_dependencies(kind: str):
    table = ROOT / kind / "table.py"
    geometry = ROOT / kind / "table_geometry.py"
    assert table.exists() and geometry.exists()

    opposite = "docx" if kind == "hwpx" else "hwpx"
    for path in (table, geometry):
        imports = _imports(path)
        assert ".backend" not in imports
        assert not [name for name in imports if ".common" in name or f".{opposite}" in name]
        assert not [name for name in imports if ".styles" in name or ".text" in name]

    # Geometry must be a one-way dependency of table operations, never the
    # other way around. This keeps a width/padding fix from pulling object
    # wrappers into the geometry policy module.
    assert ".table_geometry" in _imports(table)
    assert ".table" not in _imports(geometry)


def test_backend_modules_delegate_tables_instead_of_owning_implementation():
    for kind in ("hwpx", "docx"):
        source = (ROOT / kind / "backend.py").read_text(encoding="utf-8")
        assert "class Table(" not in source
        assert "class Row(" not in source
        assert "class Cell(" not in source
        assert "from .table import Table, Row, Cell, create_document_table" in source
        assert "return create_document_table(self.native, rows, cols, style=style)" in source


def _mm_from_hwpx(value: str | int) -> float:
    return int(value) * 25.4 / 7200.0


def _mm_from_twips(value: str | int) -> float:
    return int(value) * 25.4 / 1440.0


def _persisted_table_geometry(kind: str, path: Path) -> dict[str, float | str | list[str]]:
    if kind == "hwpx":
        with ZipFile(path) as zf:
            root = etree.fromstring(zf.read("Contents/section0.xml"))
        ns = {"hp": HP}
        table = root.xpath("./hp:p/hp:run/hp:tbl", namespaces=ns)[0]
        width = _mm_from_hwpx(table.xpath("./hp:sz", namespaces=ns)[0].get("width"))
        margin = table.xpath("./hp:inMargin", namespaces=ns)[0]
        left = _mm_from_hwpx(margin.get("left")); right = _mm_from_hwpx(margin.get("right"))
        nested = table.xpath(".//hp:tc/hp:subList/hp:p/hp:run/hp:tbl", namespaces=ns)[0]
        nested_width = _mm_from_hwpx(nested.xpath("./hp:sz", namespaces=ns)[0].get("width"))
        parent = nested.xpath("ancestor::hp:tc[1]", namespaces=ns)[0]
        parent_width = _mm_from_hwpx(parent.xpath("./hp:cellSz", namespaces=ns)[0].get("width"))
        aligns = [c.xpath("./hp:subList", namespaces=ns)[0].get("vertAlign") for c in table.xpath("./hp:tr/hp:tc", namespaces=ns)]
        return {"width": width, "left": left, "right": right, "nested": nested_width,
                "content": parent_width-left-right, "aligns": aligns}

    with ZipFile(path) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
    ns = {"w": W}
    table = root.xpath("./w:body/w:tbl", namespaces=ns)[0]
    grid = table.xpath("./w:tblGrid/w:gridCol", namespaces=ns)
    width = sum(_mm_from_twips(c.get(f"{{{W}}}w")) for c in grid)
    mar = table.xpath("./w:tblPr/w:tblCellMar", namespaces=ns)[0]
    left = _mm_from_twips(mar.xpath("./w:left", namespaces=ns)[0].get(f"{{{W}}}w"))
    right = _mm_from_twips(mar.xpath("./w:right", namespaces=ns)[0].get(f"{{{W}}}w"))
    nested = table.xpath(".//w:tc/w:tbl", namespaces=ns)[0]
    nested_width = sum(_mm_from_twips(c.get(f"{{{W}}}w")) for c in nested.xpath("./w:tblGrid/w:gridCol", namespaces=ns))
    parent = nested.xpath("ancestor::w:tc[1]", namespaces=ns)[0]
    parent_width = _mm_from_twips(parent.xpath("./w:tcPr/w:tcW", namespaces=ns)[0].get(f"{{{W}}}w"))
    aligns = []
    for c in table.xpath("./w:tr/w:tc", namespaces=ns):
        nodes = c.xpath("./w:tcPr/w:vAlign", namespaces=ns)
        aligns.append(nodes[0].get(f"{{{W}}}val") if nodes else None)
    return {"width": width, "left": left, "right": right, "nested": nested_width,
            "content": parent_width-left-right, "aligns": aligns}


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_standalone_table_backend_owns_geometry_and_nested_fit(kind: str, tmp_path: Path):
    Document = _backend_class(kind)
    doc = Document.new()
    table = doc.add_table(2, 3, style="Table Grid")
    table.cell(0, 0).merge(table.cell(1, 1)).text = "merged"
    nested = table.cell(1, 2).add_table(1, 2, style="Table Grid")
    nested.cell(0, 0).text = "A"; nested.cell(0, 1).text = "B"
    out = tmp_path / f"table-owned.{kind}"
    doc.save(out)

    geo = _persisted_table_geometry(kind, out)
    assert abs(float(geo["nested"]) - float(geo["content"])) <= 0.05
    expected = "TOP" if kind == "hwpx" else "top"
    assert set(geo["aligns"]) == {expected}


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_table_vertical_alignment_is_backend_owned(kind: str, tmp_path: Path):
    Document = _backend_class(kind)
    doc = Document.new()
    table = doc.add_table(1, 3, style="Table Grid")
    values = [WD_ALIGN_VERTICAL.TOP, WD_ALIGN_VERTICAL.CENTER, WD_ALIGN_VERTICAL.BOTTOM]
    for cell, value in zip(table.rows[0].cells, values):
        cell.vertical_alignment = value
        assert cell.vertical_alignment == value
    out = tmp_path / f"align.{kind}"
    doc.save(out)
    reopened = Document.open(out)
    assert [c.vertical_alignment for c in reopened.tables[0].rows[0].cells] == values


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_table_merge_and_nested_tables_are_backend_owned(kind: str, tmp_path: Path):
    Document = _backend_class(kind)
    doc = Document.new()
    table = doc.add_table(2, 3, style="Table Grid")
    merged = table.cell(0, 0).merge(table.cell(1, 1))
    merged.text = "merged"
    cell = table.cell(1, 2)
    cell.add_table(2, 2, style="Table Grid").cell(1, 1).text = "nested"
    assert len(table.rows) == 2
    # Both backends expose logical grid cells, so merged spans repeat the same
    # logical cell proxy slots just like python-docx does.
    assert len(table.rows[0].cells) == 3
    assert len(cell.tables) == 1
    out = tmp_path / f"merge.{kind}"
    doc.save(out)
    reopened = Document.open(out)
    assert len(reopened.tables) == 1
    assert reopened.tables[0].cell(0, 0).text == "merged"
    assert reopened.tables[0].cell(1, 2).tables[0].cell(1, 1).text == "nested"

@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_column_width_uses_shared_physical_length_contract(kind: str, tmp_path: Path):
    from pywpdoc._engine import Mm
    Document = _backend_class(kind)
    doc = Document.new()
    table = doc.add_table(2, 3, style="Table Grid")
    table.columns[0].width = Mm(30)
    assert abs(table.columns[0].width.mm - 30.0) <= 0.05
    # Column width is a rendered geometry contract, not only a grid hint.
    assert all(abs(cell.width.mm - 30.0) <= 0.05 for cell in table.columns[0].cells)
    out = tmp_path / f"column-width.{kind}"
    doc.save(out)
    reopened = Document.open(out)
    assert abs(reopened.tables[0].columns[0].width.mm - 30.0) <= 0.05
    assert all(abs(cell.width.mm - 30.0) <= 0.05 for cell in reopened.tables[0].columns[0].cells)


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_row_height_uses_shared_physical_length_contract(kind: str, tmp_path: Path):
    from pywpdoc._engine import Mm
    Document = _backend_class(kind)
    doc = Document.new()
    table = doc.add_table(2, 2, style="Table Grid")
    table.rows[0].height = Mm(18)
    assert abs(table.rows[0].height.mm - 18.0) <= 0.05
    out = tmp_path / f"row-height.{kind}"
    doc.save(out)
    reopened = Document.open(out)
    assert abs(reopened.tables[0].rows[0].height.mm - 18.0) <= 0.05


def test_table_public_types_are_owned_by_table_modules():
    from pywpdoc._engine.docx import Table as DocxTable, Row as DocxRow, Column as DocxColumn, Cell as DocxCell
    from pywpdoc._engine.hwpx import Table as HwpxTable, Row as HwpxRow, Column as HwpxColumn, Cell as HwpxCell
    for kind, classes in (("docx", (DocxTable, DocxRow, DocxColumn, DocxCell)), ("hwpx", (HwpxTable, HwpxRow, HwpxColumn, HwpxCell))):
        assert all(cls.__module__ == f"pywpdoc._engine.{kind}.table" for cls in classes)
