"""DOCX-owned import/export of backend-neutral Common rebuild snapshots."""
from __future__ import annotations

from io import BytesIO
from typing import Any

from ..core.snapshot import DocumentSnapshot


def _imports():
    try:
        from docx import Document as DocxDocument
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE
        from docx.shared import Pt, Mm
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.dml.color import RGBColor
    except ImportError as exc:  # pragma: no cover
        raise ImportError("DOCX support requires the optional dependency 'python-docx>=1.2,<2'") from exc
    return DocxDocument, WD_ALIGN_PARAGRAPH, WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE, Pt, Mm, OxmlElement, qn, RGBColor


def _pt_from_hwp(value: int | float) -> float:
    return float(value) / 100.0


def _mm_from_hwp(value: int | float) -> float:
    return float(value) * 25.4 / 7200.0


def _set_cell_margins(cell, margins: dict[str, int]) -> None:
    *_, OxmlElement, qn, _ = _imports()
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = tcPr.first_child_found_in("w:tcMar")
    if tcMar is None:
        tcMar = OxmlElement("w:tcMar")
        tcPr.append(tcMar)
    for side in ("top", "left", "bottom", "right"):
        tag = "w:" + side
        node = tcMar.find(qn(tag))
        if node is None:
            node = OxmlElement(tag); tcMar.append(node)
        # HWPUNIT -> twentieths of a point (twips)
        node.set(qn("w:w"), str(round(_pt_from_hwp(margins.get(side, 0)) * 20)))
        node.set(qn("w:type"), "dxa")


def _set_cell_border(cell, *, color: str = "000000", size_eighth_pt: int = 8) -> None:
    *_, OxmlElement, qn, _ = _imports()
    tcPr = cell._tc.get_or_add_tcPr()
    borders = tcPr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders"); tcPr.append(borders)
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + side
        node = borders.find(qn(tag))
        if node is None:
            node = OxmlElement(tag); borders.append(node)
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), str(size_eighth_pt))
        node.set(qn("w:space"), "0")
        node.set(qn("w:color"), color.lstrip("#"))


def _set_cell_native_border(cell, spec: dict[str, Any]) -> None:
    """Replace a Word cell's four edge borders with the HWPX borderFill sides.

    A cell is initially given a neutral default border while the Word table is
    built.  Native HWPX border data must *replace* those defaults, not append a
    second ``w:top``/``w:bottom`` etc.  Duplicate side elements are malformed
    OOXML and different Word-compatible renderers choose different copies; in
    particular the lower outline of a table can disappear.
    """
    *_, OxmlElement, qn, _ = _imports()
    tcPr = cell._tc.get_or_add_tcPr()
    fill = spec.get("fill")
    if fill:
        shd = tcPr.first_child_found_in("w:shd")
        if shd is None:
            shd = OxmlElement("w:shd"); tcPr.append(shd)
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:fill"), str(fill).lstrip("#")[-6:])

    borders = tcPr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcPr.append(borders)
    else:
        # python-docx has no public per-cell border API, so this backend writes
        # the small OOXML fragment directly.  Remove the provisional/default
        # sides first so every edge has exactly one authoritative element.
        for child in list(borders):
            borders.remove(child)

    sides = spec.get("sides") or {}
    mapping = (("topBorder", "top"), ("leftBorder", "left"),
               ("bottomBorder", "bottom"), ("rightBorder", "right"))
    for src_name, dst_name in mapping:
        src = sides.get(src_name)
        if not src:
            continue
        node = OxmlElement("w:" + dst_name)
        if str(src.get("type", "NONE")) == "NONE":
            node.set(qn("w:val"), "nil")
        else:
            node.set(qn("w:val"), "single")
            width = str(src.get("width", "0.12 mm"))
            try:
                mm = float(width.lower().replace("mm", "").strip())
                sz = max(2, round(mm / 25.4 * 72 * 8))
            except Exception:
                sz = 3
            node.set(qn("w:sz"), str(sz))
            node.set(qn("w:color"), str(src.get("color", "#000000")).lstrip("#")[-6:])
            node.set(qn("w:space"), "0")
        borders.append(node)


def _remove_cell_borders(cell) -> None:
    *_, OxmlElement, qn, _ = _imports()
    tcPr = cell._tc.get_or_add_tcPr()
    borders = tcPr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders"); tcPr.append(borders)
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = OxmlElement("w:" + side)
        node.set(qn("w:val"), "nil")
        borders.append(node)


def _set_table_width(table, width_hwp: int) -> None:
    *_, OxmlElement, qn, _ = _imports()
    table.autofit = False
    tblPr = table._tbl.tblPr
    tblW = tblPr.first_child_found_in("w:tblW")
    if tblW is None:
        tblW = OxmlElement("w:tblW"); tblPr.append(tblW)
    tblW.set(qn("w:type"), "dxa")
    tblW.set(qn("w:w"), str(round(_pt_from_hwp(width_hwp) * 20)))


def _set_table_borders_none(table) -> None:
    *_, OxmlElement, qn, _ = _imports()
    tblPr = table._tbl.tblPr
    borders = tblPr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders"); tblPr.append(borders)
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = OxmlElement("w:" + side); node.set(qn("w:val"), "nil"); borders.append(node)


def _clear_paragraph(p) -> None:
    for child in list(p._p):
        if child.tag.endswith('}pPr'):
            continue
        p._p.remove(child)


def _apply_paragraph_format(p, fmt: dict[str, Any]) -> None:
    _, WD_ALIGN_PARAGRAPH, _, _, Pt, _, _, _, _ = _imports()
    amap = {
        "LEFT": WD_ALIGN_PARAGRAPH.LEFT, "CENTER": WD_ALIGN_PARAGRAPH.CENTER,
        "RIGHT": WD_ALIGN_PARAGRAPH.RIGHT, "JUSTIFY": WD_ALIGN_PARAGRAPH.JUSTIFY,
        "DISTRIBUTE": WD_ALIGN_PARAGRAPH.DISTRIBUTE,
    }
    p.alignment = amap.get(str(fmt.get("align", "JUSTIFY")), WD_ALIGN_PARAGRAPH.JUSTIFY)
    pf = p.paragraph_format
    if fmt.get("left") is not None: pf.left_indent = Pt(_pt_from_hwp(fmt.get("left", 0)))
    if fmt.get("right") is not None: pf.right_indent = Pt(_pt_from_hwp(fmt.get("right", 0)))
    if fmt.get("first") is not None: pf.first_line_indent = Pt(_pt_from_hwp(fmt.get("first", 0)))
    pf.space_before = Pt(_pt_from_hwp(fmt.get("space_before", 0)))
    pf.space_after = Pt(_pt_from_hwp(fmt.get("space_after", 0)))
    if fmt.get("line_spacing_type") == "PERCENT":
        pf.line_spacing = max(0.1, float(fmt.get("line_spacing", 160)) / 100.0)


def _apply_run_format(run, fmt: dict[str, Any]) -> None:
    *_, Pt, _, OxmlElement, qn, RGBColor = _imports()
    font = run.font
    name = fmt.get("font") or None
    if name:
        font.name = name
        rPr = run._r.get_or_add_rPr()
        rFonts = rPr.rFonts
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts"); rPr.insert(0, rFonts)
        for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
            rFonts.set(qn("w:" + attr), name)
    if fmt.get("size_pt"):
        font.size = Pt(float(fmt["size_pt"]))
    font.bold = bool(fmt.get("bold", False)); font.italic = bool(fmt.get("italic", False))
    font.underline = bool(fmt.get("underline", False)); font.strike = bool(fmt.get("strike", False))
    color = str(fmt.get("color") or "#000000").lstrip("#")
    if len(color) == 6:
        try: font.color.rgb = RGBColor.from_string(color.upper())
        except Exception: pass
    rPr = run._r.get_or_add_rPr()
    ratio = int(fmt.get("ratio", 100) or 100)
    if ratio != 100:
        w = OxmlElement("w:w"); w.set(qn("w:val"), str(max(1, ratio))); rPr.append(w)
    sp = int(fmt.get("spacing_percent", 0) or 0)
    if sp:
        # HWPX spacing is percentage of glyph size; Word spacing is twips.
        points = float(fmt.get("size_pt", 10.0)) * sp / 100.0
        el = OxmlElement("w:spacing"); el.set(qn("w:val"), str(round(points * 20))); rPr.append(el)


def _append_picture(run, item: dict[str, Any]) -> None:
    _, _, _, _, _, Mm, _, _, _ = _imports()
    data = item.get("data")
    if not data: return
    width = Mm(_mm_from_hwp(item.get("width", 0))) if item.get("width") else None
    height = Mm(_mm_from_hwp(item.get("height", 0))) if item.get("height") else None
    run.add_picture(BytesIO(data), width=width, height=height)


def _fill_paragraph(p, block: dict[str, Any], *, next_layout_top: int | None = None) -> None:
    _clear_paragraph(p)
    _apply_paragraph_format(p, block.get("format", {}))
    lines = block.get("layout_lines") or []
    if lines:
        _, _, _, _, Pt, _, _, _, _ = _imports()
        try:
            from docx.enum.text import WD_LINE_SPACING
            # Use Hancom's measured rendered horizontal start rather than the
            # semantic hanging-indent values, which are not 1:1 Word indents.
            p.paragraph_format.left_indent = Pt(_pt_from_hwp(int(lines[0].get("horz", 0))))
            p.paragraph_format.first_line_indent = Pt(0)
            if len(lines) >= 2:
                advance = int(lines[1].get("top", 0)) - int(lines[0].get("top", 0))
            elif next_layout_top is not None:
                # For a single rendered line, the next paragraph's cached
                # top is the best available measurement of the complete
                # line box.  Do not add hp:lineseg/@spacing again: that
                # value is already folded into Hancom's next cached top.
                advance = int(next_layout_top) - int(lines[0].get("top", 0))
            else:
                advance = int(lines[0].get("height", 0)) + int(lines[0].get("spacing", 0))
            if advance > 0:
                p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
                p.paragraph_format.line_spacing = Pt(_pt_from_hwp(advance))
            # Paragraph spacing is already represented by the measured line
            # tops above (and by paraPr before/after where present).  Treating
            # lineseg/@spacing as Word space-after double-counts the gap and
            # makes tightly packed HWPX boxes overflow vertically.
            p.paragraph_format.space_after = Pt(0)
        except Exception:
            pass
    # A paragraph that only anchors a nested table/object has a cached
    # lineseg for the object in HWPX.  If that measured extent is also
    # assigned to Word's mandatory host paragraph, then appending the table
    # counts the object height twice and clips the tail of fixed-layout boxes.
    # Keep the host paragraph effectively zero-height; the nested table itself
    # supplies the visible extent.
    items = block.get("items", [])
    if any(item.get("type") == "table" for item in items) and not any(
        item.get("type") == "text" and item.get("text") for item in items
    ):
        try:
            from docx.enum.text import WD_LINE_SPACING
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
            p.paragraph_format.line_spacing = Pt(1)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
        except Exception:
            pass
    for item in items:
        typ = item.get("type")
        if typ == "text":
            r = p.add_run(item.get("text", "")); _apply_run_format(r, item.get("format", {}))
        elif typ == "picture":
            r = p.add_run(); _append_picture(r, item)
        # Nested tables/boxes are handled by the owning cell builder.


def _clear_cell_content(cell) -> None:
    # Keep one paragraph and delete nested tables/extra paragraphs.
    tc = cell._tc
    ps = list(tc.p_lst)
    keep = ps[0] if ps else None
    for child in list(tc):
        if child.tag.endswith('}tcPr'): continue
        if keep is not None and child is keep: continue
        tc.remove(child)
    if keep is None:
        cell.add_paragraph()


def _fill_borderless_nested_table_line(p, block: dict[str, Any]) -> bool:
    """Render the source's borderless one-row consent grid in its host paragraph.

    Hancom stores the checkbox line as a tiny 1x4 borderless table embedded in
    a paragraph.  Word already needs that host paragraph, so placing another
    nested table below it counts vertical extent twice.  Use the same host
    paragraph with a tab stop at the original third-cell start instead.
    """
    if int(block.get("rows", 0)) != 1 or int(block.get("cols", 0)) < 3:
        return False
    cells = sorted(block.get("cells", []), key=lambda c: int(c.get("col", 0)))
    visible = []
    for c in cells:
        items = []
        for pb in c.get("paragraphs", []):
            items.extend(pb.get("items", []))
        if any(it.get("type") == "text" and it.get("text") for it in items):
            visible.append((c, items))
    if len(visible) != 2:
        return False
    _, _, _, _, Pt, _, _, _, _ = _imports()
    _clear_paragraph(p)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    try:
        from docx.enum.text import WD_LINE_SPACING
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        # The source embedded table's own height is the measured extent of
        # this final line inside the HWPX rectangle.
        line_height = _pt_from_hwp(int(block.get("height", 0) or 1000))
        p.paragraph_format.line_spacing = Pt(max(1.0, line_height))
    except Exception:
        pass
    first_cell, first_items = visible[0]
    second_cell, second_items = visible[1]
    for it in first_items:
        if it.get("type") == "text":
            r = p.add_run(it.get("text", "")); _apply_run_format(r, it.get("format", {}))
    second_col = int(second_cell.get("col", 0))
    tab_pos = sum(int(c.get("width", 0) or 0) for c in cells if int(c.get("col", 0)) < second_col)
    try:
        p.paragraph_format.tab_stops.add_tab_stop(Pt(_pt_from_hwp(tab_pos)))
        p.add_run("\t")
    except Exception:
        p.add_run("    ")
    for it in second_items:
        if it.get("type") == "text":
            r = p.add_run(it.get("text", "")); _apply_run_format(r, it.get("format", {}))
    return True


def _build_table(parent, block: dict[str, Any], *, box: bool = False):
    _, _, VAlign, RowRule, Pt, Mm, OxmlElement, qn, _ = _imports()
    rows = max(1, int(block.get("rows", 1))); cols = max(1, int(block.get("cols", 1)))
    table = parent.add_table(rows=rows, cols=cols)
    _set_table_width(table, int(block.get("width", 0)))
    # Reconstruct the source grid from any single-span cells. python-docx
    # otherwise leaves a uniform tblGrid even when individual cell widths are set.
    grid_widths = [0] * cols
    for c in block.get("cells", []):
        col = int(c.get("col", 0)); span = max(1, int(c.get("col_span", 1))); width = int(c.get("width", 0) or 0)
        if width <= 0 or col >= cols: continue
        if span == 1:
            grid_widths[col] = max(grid_widths[col], width)
        else:
            share = round(width / span)
            for j in range(col, min(cols, col + span)):
                if grid_widths[j] == 0: grid_widths[j] = share
    fallback = round(int(block.get("width",0) or 0) / cols) if cols else 0
    for j in range(cols):
        if grid_widths[j] == 0: grid_widths[j] = fallback
        if grid_widths[j] > 0:
            table.columns[j].width = Mm(_mm_from_hwp(grid_widths[j]))
            for cc in table.columns[j].cells:
                cc.width = Mm(_mm_from_hwp(grid_widths[j]))
    if box:
        color = str(block.get("line_color", "#000000"));
        for row in table.rows:
            for cell in row.cells:
                _set_cell_border(cell, color=color, size_eighth_pt=8)
    else:
        for row in table.rows:
            for cell in row.cells: _set_cell_border(cell)
    anchors: dict[tuple[int,int], Any] = {}
    for c in block.get("cells", []):
        r = int(c.get("row", 0)); col = int(c.get("col", 0))
        if r >= rows or col >= cols: continue
        cell = table.cell(r, col)
        rs = max(1, int(c.get("row_span", 1))); cs = max(1, int(c.get("col_span", 1)))
        if rs > 1 or cs > 1:
            cell = cell.merge(table.cell(min(rows-1,r+rs-1), min(cols-1,col+cs-1)))
        anchors[(r,col)] = cell
        _clear_cell_content(cell)
        _set_cell_margins(cell, c.get("margins", {"left":510,"right":510,"top":141,"bottom":141}))
        if c.get("border"):
            _set_cell_native_border(cell, c.get("border", {}))
        va = str(c.get("vert_align","TOP"))
        cell.vertical_alignment = {"TOP":VAlign.TOP,"CENTER":VAlign.CENTER,"BOTTOM":VAlign.BOTTOM}.get(va,VAlign.TOP)
        paragraphs = c.get("paragraphs", [])
        if paragraphs:
            def _next_top(index: int) -> int | None:
                if index + 1 >= len(paragraphs):
                    return None
                nxt = paragraphs[index + 1].get("layout_lines") or []
                return int(nxt[0].get("top", 0)) if nxt else None
            word_paragraphs = [cell.paragraphs[0]]
            _fill_paragraph(word_paragraphs[0], paragraphs[0], next_layout_top=_next_top(0))
            for pi, pb in enumerate(paragraphs[1:], start=1):
                wp = cell.add_paragraph(); word_paragraphs.append(wp)
                _fill_paragraph(wp, pb, next_layout_top=_next_top(pi))
            # Nested blocks inside paragraph items.  A tiny borderless
            # consent grid is a positioning device in this source.  Render
            # it in the same host paragraph to preserve the cached HWPX slot.
            for pi, pb in enumerate(paragraphs):
                for item in pb.get("items", []):
                    if item.get("type") == "table":
                        if not _fill_borderless_nested_table_line(word_paragraphs[pi], item):
                            _build_table(cell, item)
        else:
            _clear_paragraph(cell.paragraphs[0])
        # cell width
        if c.get("width"):
            cell.width = Mm(_mm_from_hwp(c["width"]))
    # row heights from source cell geometry (exact where possible)
    for ri,row in enumerate(table.rows):
        h = max([int(c.get("height",0)) for c in block.get("cells",[]) if int(c.get("row",-1))==ri] or [0])
        if h:
            row.height = Pt(_pt_from_hwp(h))
            # Newly-authored HWPX tables without a measured layout may retain
            # placeholder cell heights below the font's minimum line height.
            # Forcing that tiny value as Word EXACTLY clips the visible cell
            # text although the OOXML still contains it. Allow growth instead.
            row.height_rule = RowRule.AT_LEAST if h < 900 else RowRule.EXACTLY
    return table


def _build_compact_text_box(parent, block: dict[str, Any]):
    """Build a fixed HWPX text box as one Word paragraph when possible.

    Multiple Word paragraphs have per-paragraph layout overhead that does not
    exist in Hancom's cached lineseg coordinates.  For a box whose source
    paragraphs are all single-line and whose only embedded object is the
    small borderless positioning grid, one paragraph with explicit line
    breaks is the closest Word analogue and preserves the measured height.
    """
    paragraphs = block.get("paragraphs", [])
    if not paragraphs or any(len(pb.get("layout_lines") or []) > 1 for pb in paragraphs):
        return None
    nested = [it for pb in paragraphs for it in pb.get("items", []) if it.get("type") == "table"]
    if len(nested) != 1:
        return None
    _, _, VAlign, _, Pt, _, _, _, _ = _imports()
    table = parent.add_table(rows=1, cols=1)
    _set_table_width(table, int(block.get("width", 0)))
    table.autofit = False
    cell = table.cell(0, 0)
    _set_cell_border(cell, color=str(block.get("line_color", "#000000")), size_eighth_pt=8)
    _set_cell_margins(cell, {"left":0,"right":0,"top":0,"bottom":0})
    cell.vertical_alignment = VAlign.TOP
    _clear_cell_content(cell)
    p = cell.paragraphs[0]
    _clear_paragraph(p)
    p.paragraph_format.space_before = Pt(_pt_from_hwp(int((paragraphs[0].get("format") or {}).get("space_before", 0) or 0)))
    p.paragraph_format.space_after = Pt(0)
    tops = []
    for pb in paragraphs:
        lines = pb.get("layout_lines") or []
        if lines: tops.append(int(lines[0].get("top", 0)))
    diffs = [b-a for a,b in zip(tops,tops[1:]) if b>a]
    try:
        from statistics import median
        from docx.enum.text import WD_LINE_SPACING
        advance = float(median(diffs)) if diffs else 1492.0
        embedded_height = float(int(nested[0].get("height", 0) or 0))
        if embedded_height > 0:
            advance = min(advance, embedded_height)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        p.paragraph_format.line_spacing = Pt(_pt_from_hwp(advance))
    except Exception:
        pass

    def append_text_items(items):
        for it in items:
            if it.get("type") == "text":
                r = p.add_run(it.get("text", "")); _apply_run_format(r, it.get("format", {}))

    for pi, pb in enumerate(paragraphs):
        if pi:
            p.add_run().add_break()
        for item in pb.get("items", []):
            if item.get("type") == "text":
                r = p.add_run(item.get("text", "")); _apply_run_format(r, item.get("format", {}))
            elif item.get("type") == "table":
                cells = sorted(item.get("cells", []), key=lambda c: int(c.get("col", 0)))
                visible = []
                for c in cells:
                    items = []
                    for cp in c.get("paragraphs", []): items.extend(cp.get("items", []))
                    if any(it.get("type") == "text" and it.get("text") for it in items):
                        visible.append((c, items))
                if len(visible) == 2:
                    first_cell, first_items = visible[0]; second_cell, second_items = visible[1]
                    append_text_items(first_items)
                    second_col = int(second_cell.get("col", 0))
                    tab_pos = sum(int(c.get("width",0) or 0) for c in cells if int(c.get("col",0)) < second_col)
                    try:
                        p.paragraph_format.tab_stops.add_tab_stop(Pt(_pt_from_hwp(tab_pos)))
                        p.add_run("\t")
                    except Exception:
                        p.add_run("    ")
                    append_text_items(second_items)
                else:
                    return None
    return table


def _build_box(parent, block: dict[str, Any]):
    compact = _build_compact_text_box(parent, block)
    if compact is not None:
        return compact
    # A one-cell fixed-size table is the most interoperable Word analogue of
    # the HWPX rectangle/text-box while retaining exact physical geometry.
    # Do not force the HWPX hp:sz height onto a Word table row. For floating
    # HWPX rectangles that value is not the full flow extent; the paragraph
    # lineseg slot carried by the outer layout row is the authoritative
    # pagination measurement. Let the inner Word box grow to its text.
    b = {"rows":1,"cols":1,"width":block.get("width",0),"height":0,
         "line_color":block.get("line_color","#000000"),"cells":[{"row":0,"col":0,"width":block.get("width",0),"height":0,"vert_align":"TOP","margins":{"left":0,"right":0,"top":0,"bottom":0},"paragraphs":block.get("paragraphs",[])}]}
    return _build_table(parent, b, box=True)


def _build_layout_table(doc, portable: dict[str, Any]):
    _, _, _, RowRule, Pt, Mm, _, _, _ = _imports()
    page = portable.get("page", {})
    body_width = max(1, int(page.get("width",59528)) - int(page.get("left",0)) - int(page.get("right",0)))
    blocks = portable.get("blocks", [])
    outer = doc.add_table(rows=max(1,len(blocks)), cols=1)
    _set_table_width(outer, body_width); _set_table_borders_none(outer); outer.autofit=False
    for idx, block in enumerate(blocks):
        row = outer.rows[idx]
        slot = int(block.get("layout",{}).get("slot_height",0) or 0)
        if slot:
            row.height = Pt(_pt_from_hwp(slot)); row.height_rule = RowRule.AT_LEAST
        cell = row.cells[0]; _remove_cell_borders(cell); _set_cell_margins(cell,{"left":0,"right":0,"top":0,"bottom":0}); _clear_cell_content(cell)
        typ = block.get("type")
        if typ == "paragraph":
            _fill_paragraph(cell.paragraphs[0], block)
        elif typ == "table":
            # Minimize the cell's mandatory paragraph before the nested table.
            p=cell.paragraphs[0]; _clear_paragraph(p); p.paragraph_format.space_before=Pt(0); p.paragraph_format.space_after=Pt(0); p.add_run().font.size=Pt(1)
            _build_table(cell, block)
        elif typ == "box":
            p=cell.paragraphs[0]; _clear_paragraph(p); p.paragraph_format.space_before=Pt(0); p.paragraph_format.space_after=Pt(0); p.add_run().font.size=Pt(1)
            _build_box(cell, block)
        elif typ == "picture":
            p=cell.paragraphs[0]; r=p.add_run(); _append_picture(r,block)
    return outer


def import_snapshot(snapshot: DocumentSnapshot):
    DocxDocument, _, _, _, _, Mm, _, _, _ = _imports()
    # Rebuild of a DOCX snapshot must restore the complete native package.
    # An empty portable snapshot does NOT describe an empty source document.
    if snapshot.source_format == "docx":
        native_package = snapshot.native_payload.get("docx_package")
        if not isinstance(native_package, (bytes, bytearray)):
            from ..core.errors import DocumentUnsupportedError
            raise DocumentUnsupportedError(
                "DOCX rebuild requires an intact DOCX native payload",
                code="docx-snapshot-native-payload-required",
            )
        return DocxDocument(BytesIO(native_package))
    doc = DocxDocument()
    sec = doc.sections[0]
    page = snapshot.portable.get("page", {})
    sec.page_width = Mm(_mm_from_hwp(page.get("width",59528))); sec.page_height = Mm(_mm_from_hwp(page.get("height",84186)))
    sec.left_margin = Mm(_mm_from_hwp(page.get("left",0))); sec.right_margin = Mm(_mm_from_hwp(page.get("right",0)))
    sec.top_margin = Mm(_mm_from_hwp(page.get("top",0))); sec.bottom_margin = Mm(_mm_from_hwp(page.get("bottom",0)))
    # HWPX header/footer fields are reserved areas, not Word offsets. The source
    # sample has zero; do not invent a mapping here.
    sec.header_distance = Mm(0); sec.footer_distance = Mm(0)
    # Remove default empty body paragraph before adding the fixed-layout table.
    body = doc._element.body
    for child in list(body):
        if child.tag.endswith('}sectPr'): continue
        body.remove(child)
    _build_layout_table(doc, snapshot.portable)
    return doc


def export_snapshot(native, *, preserve_layout: bool = True) -> DocumentSnapshot:
    # Minimal same-backend transport; cross-format DOCX->HWPX is intentionally
    # not claimed by this release.
    bio = BytesIO(); native.save(bio)
    return DocumentSnapshot(source_format="docx", portable={}, native_payload={"docx_package": bio.getvalue()})


__all__ = ["import_snapshot", "export_snapshot"]
