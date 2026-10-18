"""Grid, rows, nested cells and merge contracts, tested on both formats."""
from __future__ import annotations
import pytest


@pytest.mark.common_api
@pytest.mark.parametrize("rows,cols", [(1,1), (1,3), (2,2), (3,1), (4,3)])
def test_table_grid_persists(document, save_reopen, rows, cols):
    t = document.add_table(rows, cols)
    for i in range(rows):
        for j in range(cols):
            t.cell(i, j).text = f"[{i}:{j}]"
    opened, _ = save_reopen(document)
    actual = opened.tables[0]
    assert len(actual.rows) == rows
    for i in range(rows):
        for j in range(cols):
            assert actual.cell(i, j).text == f"[{i}:{j}]"


@pytest.mark.common_api
@pytest.mark.parametrize("extra", [1, 2, 4])
def test_add_rows_keeps_prior_cells(document, save_reopen, extra):
    table = document.add_table(1, 2)
    table.cell(0, 0).text = "KEY"
    table.cell(0, 1).text = "VALUE"
    for i in range(extra):
        row = table.add_row()
        row.cells[0].text = f"K{i}"
        row.cells[1].text = f"V{i}"
    opened, _ = save_reopen(document)
    t2 = opened.tables[0]
    assert len(t2.rows) == 1 + extra
    assert t2.cell(0, 0).text == "KEY"
    assert t2.cell(extra, 1).text == f"V{extra-1}"


@pytest.mark.common_api
@pytest.mark.parametrize("axis", ["horizontal", "vertical"])
def test_table_merge_cell_contents_are_accessible(document, save_reopen, axis):
    table = document.add_table(2, 2)
    table.cell(0, 0).text = "합쳐진 셀"
    target = table.cell(0, 1) if axis == "horizontal" else table.cell(1, 0)
    table.cell(0, 0).merge(target)
    opened, _ = save_reopen(document)
    assert "합쳐진 셀" in opened.tables[0].cell(0, 0).text


@pytest.mark.common_api
def test_nested_table_survives_roundtrip(document, save_reopen):
    outside = document.add_table(1, 1)
    inside = outside.cell(0, 0).add_table(2, 1)
    inside.cell(1, 0).text = "nested-data"
    opened, _ = save_reopen(document)
    assert opened.tables[0].cell(0, 0).tables[0].cell(1, 0).text == "nested-data"


@pytest.mark.common_api
def test_two_tables_keep_order_and_independent_contents(document, save_reopen):
    a = document.add_table(1, 1)
    a.cell(0, 0).text = "A"
    b = document.add_table(1, 1)
    b.cell(0, 0).text = "B"
    opened, _ = save_reopen(document)
    assert [t.cell(0, 0).text for t in opened.tables] == ["A", "B"]
