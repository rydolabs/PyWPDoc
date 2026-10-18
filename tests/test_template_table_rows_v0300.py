"""v0.30 structure-preserving table-row template repetition."""
from __future__ import annotations

from pathlib import Path

import pytest

from pywpdoc import Document, DocumentUnsupportedError, DocumentValueError
from pywpdoc._engine import Mm, WD_ALIGN_VERTICAL


def _template(fmt: str):
    doc = Document.new(fmt)
    table = doc.add_table(2, 3, style="Table Grid")
    table.cell(0, 0).text = "Name"
    table.cell(0, 1).text = "Qty"
    table.cell(0, 2).text = "Company"
    table.cell(1, 0).text = "{{#items}}{{name}}"
    table.cell(1, 1).text = "{{qty}}"
    table.cell(1, 2).text = "{{company}}{{/items}}"
    return doc, table


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_table_row_repeat_uses_item_context_and_parent_fallback(fmt: str, tmp_path: Path):
    doc, table = _template(fmt)
    changed = doc.render_template(
        {
            "company": "ACME",
            "items": [
                {"name": "A", "qty": 1},
                {"name": "B", "qty": 2},
            ],
        },
        sections=True,
        table_rows=True,
    )
    assert changed > 0
    assert [[cell.text for cell in row.cells] for row in table.rows] == [
        ["Name", "Qty", "Company"],
        ["A", "1", "ACME"],
        ["B", "2", "ACME"],
    ]
    out = tmp_path / f"repeat.{fmt}"
    doc.save(out)
    reopened = Document.open(out)
    assert [[cell.text for cell in row.cells] for row in reopened.tables[0].rows] == [
        ["Name", "Qty", "Company"],
        ["A", "1", "ACME"],
        ["B", "2", "ACME"],
    ]


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_table_row_repeat_empty_sequence_removes_template_row(fmt: str):
    doc, table = _template(fmt)
    doc.render_template(
        {"company": "ACME", "items": []},
        sections=True,
        table_rows=True,
    )
    assert len(table.rows) == 1
    assert [cell.text for cell in table.rows[0].cells] == ["Name", "Qty", "Company"]


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_inverted_table_row_section_is_structural_condition(fmt: str):
    doc = Document.new(fmt)
    table = doc.add_table(2, 1, style="Table Grid")
    table.cell(0, 0).text = "Header"
    table.cell(1, 0).text = "{{^items}}No items for {{company}}{{/items}}"

    doc.render_template(
        {"company": "ACME", "items": []},
        sections=True,
        table_rows=True,
    )
    assert [row.cells[0].text for row in table.rows] == ["Header", "No items for ACME"]


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_inline_cell_section_is_not_promoted_to_whole_row_repeat(fmt: str):
    doc = Document.new(fmt)
    table = doc.add_table(1, 2, style="Table Grid")
    table.cell(0, 0).text = "Status: {{#active}}Yes{{/active}}"
    table.cell(0, 1).text = "{{name}}"

    doc.render_template(
        {"active": False, "name": "A"},
        sections=True,
        table_rows=True,
    )
    assert len(table.rows) == 1
    assert [cell.text for cell in table.rows[0].cells] == ["Status: ", "A"]


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_table_row_repeat_preserves_row_and_cell_structure(fmt: str, tmp_path: Path):
    doc = Document.new(fmt)
    table = doc.add_table(3, 3, style="Table Grid")
    table.cell(0, 0).text = "Header"
    template = table.rows[1]
    template.height = Mm(17)
    merged = table.cell(1, 0).merge(table.cell(1, 1))
    merged.text = "{{#items}}{{name}}"
    table.cell(1, 2).vertical_alignment = WD_ALIGN_VERTICAL.BOTTOM
    nested = table.cell(1, 2).add_table(1, 1, style="Table Grid")
    nested.cell(0, 0).text = "{{detail}}"
    table.cell(1, 2).paragraphs[-1].text = "{{/items}}"
    table.cell(2, 0).text = "Footer"

    doc.render_template(
        {"items": [{"name": "A", "detail": "x"}, {"name": "B", "detail": "y"}]},
        sections=True,
        table_rows=True,
    )
    assert len(table.rows) == 4
    for idx, (name, detail) in enumerate((("A", "x"), ("B", "y")), start=1):
        row = table.rows[idx]
        assert abs(row.height.mm - 17.0) <= 0.05
        assert row.cells[0].text == name
        assert row.cells[1].text == name
        assert row.cells[2].vertical_alignment == WD_ALIGN_VERTICAL.BOTTOM
        assert row.cells[2].tables[0].cell(0, 0).text == detail

    out = tmp_path / f"repeat-structure.{fmt}"
    doc.save(out)
    reopened = Document.open(out)
    assert len(reopened.tables[0].rows) == 4
    assert reopened.tables[0].rows[2].cells[2].tables[0].cell(0, 0).text == "y"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_fragmented_row_markers_are_supported(fmt: str):
    doc = Document.new(fmt)
    table = doc.add_table(2, 1, style="Table Grid")
    table.cell(0, 0).text = "Header"
    paragraph = table.cell(1, 0).paragraphs[0]
    paragraph.clear()
    paragraph.add_run("{{#")
    paragraph.add_run("items}}")
    paragraph.add_run("{{name}}")
    paragraph.add_run("{{/it")
    paragraph.add_run("ems}}")

    doc.render_template(
        {"items": [{"name": "A"}, {"name": "B"}]},
        sections=True,
        table_rows=True,
    )
    assert [row.cells[0].text for row in table.rows] == ["Header", "A", "B"]


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_row_render_is_single_source_pass_for_template_like_data(fmt: str):
    doc, table = _template(fmt)
    doc.render_template(
        {"company": "ROOT", "items": [{"name": "{{secret}}", "qty": 1}], "secret": "LEAK"},
        sections=True,
        table_rows=True,
    )
    assert table.rows[1].cells[0].text == "{{secret}}"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_table_row_repeat_fails_closed_on_vertical_merge(fmt: str):
    doc = Document.new(fmt)
    table = doc.add_table(3, 2, style="Table Grid")
    table.cell(0, 0).text = "Header"
    table.cell(1, 0).merge(table.cell(2, 0)).text = "{{#items}}{{name}}{{/items}}"
    with pytest.raises(DocumentUnsupportedError) as excinfo:
        doc.render_template(
            {"items": [{"name": "A"}]},
            sections=True,
            table_rows=True,
        )
    assert excinfo.value.code == "table-row-vertical-merge-unsupported"


def test_table_row_repeat_requires_explicit_section_opt_in():
    doc, _ = _template("docx")
    with pytest.raises(DocumentValueError) as excinfo:
        doc.render_template({"items": []}, table_rows=True)
    assert excinfo.value.code == "template-row-repeat-requires-sections"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_everywhere_false_preserves_historical_no_table_scope(fmt: str):
    doc, table = _template(fmt)
    changed = doc.render_template(
        {"items": [{"name": "A", "qty": 1}], "company": "ACME"},
        everywhere=False,
        sections=True,
        table_rows=True,
    )
    assert changed == 0
    assert len(table.rows) == 2
    assert table.cell(1, 0).text.startswith("{{#items}}")

@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_empty_repeat_cannot_remove_the_only_table_row(fmt: str):
    doc = Document.new(fmt)
    table = doc.add_table(1, 1, style="Table Grid")
    table.cell(0, 0).text = "{{#items}}{{name}}{{/items}}"
    with pytest.raises(DocumentUnsupportedError) as excinfo:
        doc.render_template({"items": []}, sections=True, table_rows=True)
    assert excinfo.value.code == "template-row-empty-table-unsupported"
    # Preflight rejects before mutating the template row.
    assert len(table.rows) == 1
    assert table.cell(0, 0).text == "{{#items}}{{name}}{{/items}}"
