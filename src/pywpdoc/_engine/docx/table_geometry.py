"""DOCX table geometry policy.

This module owns only physical table layout translation for the standalone DOCX
backend. It does not import the common facade, paragraph/text modules, or the
HWPX backend.
"""
from __future__ import annotations
from typing import Any

from ..core import defaults


def _imports():
    try:
        from docx.shared import Mm as DocxMm
        from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError("DOCX support requires the optional dependency 'python-docx>=1.2,<2'") from exc
    return DocxMm, WD_CELL_VERTICAL_ALIGNMENT, OxmlElement, qn


def body_width(document: Any) -> int:
    section = document.sections[-1]
    return max(int(section.page_width) - int(section.left_margin) - int(section.right_margin), 0)


def set_table_width(table: Any, target: int, cols: int) -> None:
    if cols <= 0:
        return
    qn = _imports()[-1]
    base, rem = divmod(max(int(target), 0), cols)
    widths = [base + (1 if i < rem else 0) for i in range(cols)]
    for col_index, width in enumerate(widths):
        table.columns[col_index].width = width
        for row in table.rows:
            row.cells[col_index].width = width
    tbl_w = table._tbl.tblPr.find(qn("w:tblW"))
    if tbl_w is not None:
        tbl_w.set(qn("w:type"), "dxa")
        tbl_w.set(qn("w:w"), str(round(max(int(target), 0) / 635)))
    table.autofit = False


def configure_table(table: Any) -> None:
    _, WD_CELL_VERTICAL_ALIGNMENT, OxmlElement, qn = _imports()

    def twips(mm: float) -> str:
        return str(round(float(mm) * 1440.0 / 25.4))

    tbl_pr = table._tbl.tblPr
    mar = tbl_pr.find(qn("w:tblCellMar"))
    if mar is None:
        mar = OxmlElement("w:tblCellMar")
        tbl_pr.append(mar)
    for side, value in (
        ("top", defaults.CELL_MARGIN_TOP_MM),
        ("left", defaults.CELL_MARGIN_LEFT_MM),
        ("bottom", defaults.CELL_MARGIN_BOTTOM_MM),
        ("right", defaults.CELL_MARGIN_RIGHT_MM),
    ):
        node = mar.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            mar.append(node)
        node.set(qn("w:w"), twips(value))
        node.set(qn("w:type"), "dxa")

    for row in table.rows:
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP


def fit_nested_table(table: Any, cell: Any, cols: int) -> None:
    if cols <= 0 or cell.width is None:
        return
    DocxMm = _imports()[0]
    target = max(
        int(cell.width)
        - int(DocxMm(defaults.CELL_MARGIN_LEFT_MM))
        - int(DocxMm(defaults.CELL_MARGIN_RIGHT_MM)),
        0,
    )
    set_table_width(table, target, cols)
