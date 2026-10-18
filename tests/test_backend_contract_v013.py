"""The same shared contract executed directly against each independent backend."""
from __future__ import annotations
from pathlib import Path
import pytest

from pywpdoc._engine.core import Mm, WD_ORIENT, WD_STYLE_TYPE, WD_ALIGN_VERTICAL


def backend_class(kind: str):
    if kind == "hwpx":
        from pywpdoc._engine.hwpx import Document
    else:
        from pywpdoc._engine.docx import Document
    return Document


def save_reopen(kind: str, doc, path: Path):
    doc.save(path)
    return backend_class(kind).open(path)


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_backend_contract_mixed_text(kind: str, tmp_path: Path):
    Document = backend_class(kind)
    doc = Document.new()
    p = doc.add_paragraph()
    p.add_run("A\tB\nC")
    reopened = save_reopen(kind, doc, tmp_path / f"mixed.{kind}")
    assert reopened.paragraphs[-1].text == "A\tB\nC"


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_backend_contract_table_and_nested_visibility(kind: str, tmp_path: Path):
    Document = backend_class(kind)
    doc = Document.new()
    table = doc.add_table(1, 1, style="Table Grid")
    table.cell(0, 0).text = "outer"
    table.cell(0, 0).add_table(1, 1, style="Table Grid").cell(0, 0).text = "inner"
    assert len(doc.tables) == 1
    reopened = save_reopen(kind, doc, tmp_path / f"table.{kind}")
    assert len(reopened.tables) == 1
    assert len(reopened.tables[0].cell(0, 0).tables) == 1


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_backend_contract_merge_row_is_logical_grid(kind: str, tmp_path: Path):
    Document = backend_class(kind)
    doc = Document.new()
    table = doc.add_table(2, 3, style="Table Grid")
    table.cell(0, 0).merge(table.cell(1, 1))
    assert len(table.rows[0].cells) == 3
    assert len(table.rows[1].cells) == 3
    reopened = save_reopen(kind, doc, tmp_path / f"merge.{kind}")
    assert len(reopened.tables[0].rows[0].cells) == 3


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_backend_contract_core_properties(kind: str, tmp_path: Path):
    Document = backend_class(kind)
    doc = Document.new()
    doc.core_properties.title = "Backend Contract"
    doc.core_properties.author = "Tester"
    reopened = save_reopen(kind, doc, tmp_path / f"props.{kind}")
    assert reopened.core_properties.title == "Backend Contract"
    assert reopened.core_properties.author == "Tester"


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_backend_contract_section_units_and_orientation(kind: str, tmp_path: Path):
    Document = backend_class(kind)
    doc = Document.new()
    section = doc.sections[0]
    section.left_margin = Mm(18)
    section.orientation = WD_ORIENT.LANDSCAPE
    reopened = save_reopen(kind, doc, tmp_path / f"section.{kind}")
    assert abs(reopened.sections[0].left_margin.mm - 18.0) < 0.03
    assert reopened.sections[0].orientation == WD_ORIENT.LANDSCAPE


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_backend_contract_styles_next_paragraph(kind: str, tmp_path: Path):
    Document = backend_class(kind)
    doc = Document.new()
    if kind == "hwpx":
        a = doc.styles.add_style("Backend Question", WD_STYLE_TYPE.PARAGRAPH, clone_from="Body")
        b = doc.styles.add_style("Backend Answer", WD_STYLE_TYPE.PARAGRAPH, clone_from="Body")
    else:
        a = doc.styles.add_style("Backend Question", WD_STYLE_TYPE.PARAGRAPH)
        b = doc.styles.add_style("Backend Answer", WD_STYLE_TYPE.PARAGRAPH)
    a.next_paragraph_style = b
    reopened = save_reopen(kind, doc, tmp_path / f"style.{kind}")
    assert reopened.styles["Backend Question"].next_paragraph_style.name == "Backend Answer"


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_backend_contract_structure_preserving_replace(kind: str, tmp_path: Path):
    Document = backend_class(kind)
    doc = Document.new()
    p = doc.add_paragraph()
    a = p.add_run("202")
    a.bold = True
    b = p.add_run("6학년도")
    b.italic = True
    assert doc.replace("2026", "2027") == 1
    assert p.text == "2027학년도"
    assert a.bold is True
    assert b.italic is True
    reopened = save_reopen(kind, doc, tmp_path / f"replace.{kind}")
    visible = [r for r in reopened.paragraphs[-1].runs if r.text]
    assert reopened.paragraphs[-1].text == "2027학년도"
    assert visible[0].bold is True
    assert visible[1].italic is True


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_backend_contract_cell_vertical_alignment(kind: str, tmp_path: Path):
    Document = backend_class(kind)
    doc = Document.new()
    cell = doc.add_table(1, 1, style="Table Grid").cell(0, 0)
    assert cell.vertical_alignment == WD_ALIGN_VERTICAL.TOP
    cell.vertical_alignment = WD_ALIGN_VERTICAL.BOTTOM
    reopened = save_reopen(kind, doc, tmp_path / f"vertical.{kind}")
    assert reopened.tables[0].cell(0, 0).vertical_alignment == WD_ALIGN_VERTICAL.BOTTOM
