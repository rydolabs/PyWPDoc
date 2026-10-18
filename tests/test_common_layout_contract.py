"""Persisted cross-format geometry contract for the experimental common API.

These tests intentionally read the saved package XML instead of trusting either
backend's proxy objects. They catch semantic parity that looks equal in Python
but renders at a different physical size in Word vs Hancom.
"""
from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from pywpdoc._engine.common_api import UnifiedDocument

HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _hwpunit_mm(value: str | int) -> float:
    return int(value) * 25.4 / 7200.0


def _twip_mm(value: str | int) -> float:
    return int(value) * 25.4 / 1440.0


def _qname_attr(node, local: str) -> str:
    return node.get(f"{{{W}}}{local}")


def _hwpx_layout(path: Path) -> dict:
    with ZipFile(path) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
    ns = {"hp": HP}
    page = root.xpath(".//hp:pagePr", namespaces=ns)[0]
    margin = page.xpath("./hp:margin", namespaces=ns)[0]
    tables = root.xpath("./hp:p/hp:run/hp:tbl", namespaces=ns)
    table = tables[0]
    size = table.xpath("./hp:sz", namespaces=ns)[0]

    col_count = int(table.get("colCnt"))
    col_widths = [0.0] * col_count
    merged: list[tuple[int, int, float]] = []
    for cell in table.xpath("./hp:tr/hp:tc", namespaces=ns):
        addr = cell.xpath("./hp:cellAddr", namespaces=ns)[0]
        span = cell.xpath("./hp:cellSpan", namespaces=ns)[0]
        csz = cell.xpath("./hp:cellSz", namespaces=ns)[0]
        c0 = int(addr.get("colAddr"))
        cs = int(span.get("colSpan"))
        width = _hwpunit_mm(csz.get("width"))
        if cs == 1:
            col_widths[c0] = width
        else:
            merged.append((c0, cs, width))
    for c0, cs, width in merged:
        each = width / cs
        for col in range(c0, min(c0 + cs, col_count)):
            if not col_widths[col]:
                col_widths[col] = each

    outer_cell_vertical_alignments = [
        cell.xpath("./hp:subList", namespaces=ns)[0].get("vertAlign")
        for cell in table.xpath("./hp:tr/hp:tc", namespaces=ns)
    ]
    nested = table.xpath(".//hp:tc/hp:subList/hp:p/hp:run/hp:tbl", namespaces=ns)
    nested_width = None
    nested_cell_vertical_alignments = []
    nested_parent_cell_width = None
    nested_parent_content_width = None
    table_margin = table.xpath("./hp:inMargin", namespaces=ns)[0]
    table_margin_left = _hwpunit_mm(table_margin.get("left"))
    table_margin_right = _hwpunit_mm(table_margin.get("right"))
    if nested:
        nsz = nested[0].xpath("./hp:sz", namespaces=ns)[0]
        nested_width = _hwpunit_mm(nsz.get("width"))
        nested_cell_vertical_alignments = [
            cell.xpath("./hp:subList", namespaces=ns)[0].get("vertAlign")
            for cell in nested[0].xpath("./hp:tr/hp:tc", namespaces=ns)
        ]
        parent_cell = nested[0].xpath("ancestor::hp:tc[1]", namespaces=ns)[0]
        pcsz = parent_cell.xpath("./hp:cellSz", namespaces=ns)[0]
        nested_parent_cell_width = _hwpunit_mm(pcsz.get("width"))
        if parent_cell.get("hasMargin") == "1":
            pcm = parent_cell.xpath("./hp:cellMargin", namespaces=ns)[0]
            pad_left = _hwpunit_mm(pcm.get("left"))
            pad_right = _hwpunit_mm(pcm.get("right"))
        else:
            pad_left, pad_right = table_margin_left, table_margin_right
        nested_parent_content_width = nested_parent_cell_width - pad_left - pad_right

    page_width = _hwpunit_mm(page.get("width"))
    left = _hwpunit_mm(margin.get("left"))
    right = _hwpunit_mm(margin.get("right"))
    return {
        "page_width_mm": page_width,
        "page_height_mm": _hwpunit_mm(page.get("height")),
        "left_margin_mm": left,
        "right_margin_mm": right,
        "top_margin_mm": _hwpunit_mm(margin.get("top")),
        "bottom_margin_mm": _hwpunit_mm(margin.get("bottom")),
        "body_width_mm": page_width - left - right,
        "table_width_mm": _hwpunit_mm(size.get("width")),
        "column_widths_mm": col_widths,
        "cell_margin_left_mm": table_margin_left,
        "cell_margin_right_mm": table_margin_right,
        "nested_parent_cell_width_mm": nested_parent_cell_width,
        "nested_parent_content_width_mm": nested_parent_content_width,
        "nested_table_width_mm": nested_width,
        "outer_cell_vertical_alignments": outer_cell_vertical_alignments,
        "nested_cell_vertical_alignments": nested_cell_vertical_alignments,
    }


def _docx_layout(path: Path) -> dict:
    with ZipFile(path) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
    ns = {"w": W}
    sect = root.xpath(".//w:sectPr", namespaces=ns)[-1]
    page = sect.xpath("./w:pgSz", namespaces=ns)[0]
    margin = sect.xpath("./w:pgMar", namespaces=ns)[0]
    table = root.xpath("./w:body/w:tbl", namespaces=ns)[0]
    grid = table.xpath("./w:tblGrid/w:gridCol", namespaces=ns)
    widths = [_twip_mm(_qname_attr(col, "w")) for col in grid]
    tbl_mar = table.xpath("./w:tblPr/w:tblCellMar", namespaces=ns)
    table_margin_left = table_margin_right = 0.0
    if tbl_mar:
        left_node = tbl_mar[0].xpath("./w:left", namespaces=ns)
        right_node = tbl_mar[0].xpath("./w:right", namespaces=ns)
        if left_node:
            table_margin_left = _twip_mm(_qname_attr(left_node[0], "w"))
        if right_node:
            table_margin_right = _twip_mm(_qname_attr(right_node[0], "w"))

    def cell_v_align(cell):
        nodes = cell.xpath("./w:tcPr/w:vAlign", namespaces=ns)
        return _qname_attr(nodes[0], "val") if nodes else None

    outer_cell_vertical_alignments = [
        cell_v_align(cell) for cell in table.xpath("./w:tr/w:tc", namespaces=ns)
    ]
    nested = table.xpath(".//w:tc/w:tbl", namespaces=ns)
    nested_width = None
    nested_cell_vertical_alignments = []
    nested_parent_cell_width = None
    nested_parent_content_width = None
    if nested:
        ngrid = nested[0].xpath("./w:tblGrid/w:gridCol", namespaces=ns)
        nested_width = sum(_twip_mm(_qname_attr(col, "w")) for col in ngrid)
        nested_cell_vertical_alignments = [
            cell_v_align(cell) for cell in nested[0].xpath("./w:tr/w:tc", namespaces=ns)
        ]
        parent_cell = nested[0].xpath("ancestor::w:tc[1]", namespaces=ns)[0]
        tcw = parent_cell.xpath("./w:tcPr/w:tcW", namespaces=ns)[0]
        nested_parent_cell_width = _twip_mm(_qname_attr(tcw, "w"))
        nested_parent_content_width = (
            nested_parent_cell_width - table_margin_left - table_margin_right
        )

    page_width = _twip_mm(_qname_attr(page, "w"))
    left = _twip_mm(_qname_attr(margin, "left"))
    right = _twip_mm(_qname_attr(margin, "right"))
    return {
        "page_width_mm": page_width,
        "page_height_mm": _twip_mm(_qname_attr(page, "h")),
        "left_margin_mm": left,
        "right_margin_mm": right,
        "top_margin_mm": _twip_mm(_qname_attr(margin, "top")),
        "bottom_margin_mm": _twip_mm(_qname_attr(margin, "bottom")),
        "body_width_mm": page_width - left - right,
        "table_width_mm": sum(widths),
        "column_widths_mm": widths,
        "cell_margin_left_mm": table_margin_left,
        "cell_margin_right_mm": table_margin_right,
        "nested_parent_cell_width_mm": nested_parent_cell_width,
        "nested_parent_content_width_mm": nested_parent_content_width,
        "nested_table_width_mm": nested_width,
        "outer_cell_vertical_alignments": outer_cell_vertical_alignments,
        "nested_cell_vertical_alignments": nested_cell_vertical_alignments,
    }


def _build_pair(tmp_path: Path) -> tuple[Path, Path]:
    outputs = []
    for kind in ("hwpx", "docx"):
        doc = UnifiedDocument.new(kind)
        table = doc.add_table(2, 3, style="Table Grid")
        table.cell(0, 0).text = "merge"
        table.cell(0, 0).merge(table.cell(1, 1))
        table.cell(0, 2).text = "right"
        table.cell(1, 2).add_table(1, 1, style="Table Grid").cell(0, 0).text = "nested"
        path = tmp_path / f"layout.{kind}"
        doc.save(path)
        outputs.append(path)
    return outputs[0], outputs[1]


def test_common_new_document_persisted_page_geometry_matches(tmp_path: Path):
    hwpx_path, docx_path = _build_pair(tmp_path)
    h = _hwpx_layout(hwpx_path)
    d = _docx_layout(docx_path)
    for key in (
        "page_width_mm", "page_height_mm", "left_margin_mm", "right_margin_mm",
        "top_margin_mm", "bottom_margin_mm", "body_width_mm",
    ):
        assert abs(h[key] - d[key]) <= 0.05, (key, h[key], d[key])


def test_common_default_table_fills_same_body_width(tmp_path: Path):
    hwpx_path, docx_path = _build_pair(tmp_path)
    h = _hwpx_layout(hwpx_path)
    d = _docx_layout(docx_path)
    assert abs(h["table_width_mm"] - h["body_width_mm"]) <= 0.05
    assert abs(d["table_width_mm"] - d["body_width_mm"]) <= 0.05
    assert abs(h["table_width_mm"] - d["table_width_mm"]) <= 0.05
    assert len(h["column_widths_mm"]) == len(d["column_widths_mm"]) == 3
    for hw, dw in zip(h["column_widths_mm"], d["column_widths_mm"]):
        assert abs(hw - dw) <= 0.05, (hw, dw)


def test_common_nested_table_fits_same_parent_content_box(tmp_path: Path):
    hwpx_path, docx_path = _build_pair(tmp_path)
    h = _hwpx_layout(hwpx_path)
    d = _docx_layout(docx_path)

    for key in ("cell_margin_left_mm", "cell_margin_right_mm"):
        assert abs(h[key] - d[key]) <= 0.05, (key, h[key], d[key])

    assert h["nested_parent_content_width_mm"] is not None
    assert d["nested_parent_content_width_mm"] is not None
    assert h["nested_table_width_mm"] is not None
    assert d["nested_table_width_mm"] is not None

    # Raw equal cell widths are not enough: the nested table must fit the
    # renderable content box after cell padding in both formats.
    assert abs(h["nested_table_width_mm"] - h["nested_parent_content_width_mm"]) <= 0.05
    assert abs(d["nested_table_width_mm"] - d["nested_parent_content_width_mm"]) <= 0.05
    assert abs(h["nested_table_width_mm"] - d["nested_table_width_mm"]) <= 0.05


def test_common_created_cells_persist_top_vertical_alignment(tmp_path: Path):
    hwpx_path, docx_path = _build_pair(tmp_path)
    h = _hwpx_layout(hwpx_path)
    d = _docx_layout(docx_path)
    assert h["outer_cell_vertical_alignments"]
    assert d["outer_cell_vertical_alignments"]
    assert set(h["outer_cell_vertical_alignments"]) == {"TOP"}
    assert set(d["outer_cell_vertical_alignments"]) == {"top"}
    assert set(h["nested_cell_vertical_alignments"]) == {"TOP"}
    assert set(d["nested_cell_vertical_alignments"]) == {"top"}


def test_common_cell_vertical_alignment_setter_maps_same_semantics(tmp_path: Path):
    from pywpdoc._engine import WD_ALIGN_VERTICAL

    for kind in ("hwpx", "docx"):
        doc = UnifiedDocument.new(kind)
        cell = doc.add_table(1, 1, style="Table Grid").cell(0, 0)
        assert cell.vertical_alignment == WD_ALIGN_VERTICAL.TOP
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        assert cell.vertical_alignment == WD_ALIGN_VERTICAL.CENTER
        path = tmp_path / f"vertical-center.{kind}"
        doc.save(path)
        snap = _hwpx_layout(path) if kind == "hwpx" else _docx_layout(path)
        expected = "CENTER" if kind == "hwpx" else "center"
        assert snap["outer_cell_vertical_alignments"] == [expected]
