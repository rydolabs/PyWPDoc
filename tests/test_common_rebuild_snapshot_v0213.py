from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from pywpdoc._engine.common import Document as CommonDocument
from pywpdoc._engine.hwpx import Document as HwpxDocument


def _part_hashes(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as zf:
        return {name: hashlib.sha256(zf.read(name)).hexdigest() for name in zf.namelist()}


def test_common_same_format_rebuild_preserves_hwpx_package_parts(tmp_path: Path) -> None:
    src = tmp_path / "source.hwpx"
    native = HwpxDocument.new()
    native.add_paragraph("snapshot fidelity")
    table = native.add_table(2, 2)
    table.cell(0, 0).text = "A"
    table.cell(0, 1).text = "B"
    native.save(src)

    rebuilt = CommonDocument.rebuild(src, format="hwpx", preserve_layout=True)
    out = tmp_path / "rebuilt.hwpx"
    rebuilt.save(out)

    assert _part_hashes(out) == _part_hashes(src)


def test_common_hwpx_snapshot_can_rebuild_docx(tmp_path: Path) -> None:
    src = tmp_path / "source.hwpx"
    native = HwpxDocument.new()
    native.add_paragraph("portable snapshot")
    native.save(src)

    rebuilt = CommonDocument.rebuild(src, format="docx", preserve_layout=True)
    out = tmp_path / "rebuilt.docx"
    rebuilt.save(out)

    reopened = CommonDocument.open(out)
    assert reopened.format == "docx"
    assert len(reopened.sections) == 1


def test_docx_rebuild_flattens_borderless_inline_grid_inside_text_box(tmp_path: Path) -> None:
    from pywpdoc._engine.core.snapshot import DocumentSnapshot
    from pywpdoc._engine.docx.snapshot import import_snapshot

    text_fmt = {"font": "Arial", "size_pt": 10.0, "color": "#000000", "ratio": 100, "spacing_percent": 0}
    para_fmt = {"align": "LEFT", "left": 0, "right": 0, "first": 0, "space_before": 0, "space_after": 0, "line_spacing_type": "PERCENT", "line_spacing": 160}
    consent_grid = {
        "type": "table", "rows": 1, "cols": 4, "width": 46000, "height": 1382,
        "cells": [
            {"row": 0, "col": 0, "width": 27000, "height": 1382, "paragraphs": [{"type": "paragraph", "format": para_fmt, "items": [{"type": "text", "text": "□ 동의합니다.", "format": text_fmt}], "layout_lines": [{"top": 0, "height": 1000, "spacing": 600, "horz": 0, "width": 26000}]}]},
            {"row": 0, "col": 1, "width": 1800, "height": 1382, "paragraphs": []},
            {"row": 0, "col": 2, "width": 16000, "height": 1382, "paragraphs": [{"type": "paragraph", "format": para_fmt, "items": [{"type": "text", "text": "□ 동의하지 않습니다.", "format": text_fmt}], "layout_lines": [{"top": 0, "height": 1000, "spacing": 600, "horz": 0, "width": 15000}]}]},
            {"row": 0, "col": 3, "width": 1200, "height": 1382, "paragraphs": []},
        ],
    }
    box = {
        "type": "box", "width": 47800, "height": 9200, "line_color": "#000000",
        "layout": {"top": 0, "slot_height": 10000},
        "paragraphs": [
            {"type": "paragraph", "format": para_fmt, "items": [{"type": "text", "text": "개인정보 안내", "format": text_fmt}], "layout_lines": [{"top": 0, "height": 1000, "spacing": 500, "horz": 0, "width": 47000}]},
            {"type": "paragraph", "format": para_fmt, "items": [consent_grid], "layout_lines": [{"top": 1500, "height": 1382, "spacing": 0, "horz": 0, "width": 47000}]},
        ],
    }
    snap = DocumentSnapshot(
        source_format="hwpx",
        portable={"page": {"width": 59528, "height": 84186, "left": 5669, "right": 5669, "top": 4252, "bottom": 4252}, "blocks": [box]},
    )
    native = import_snapshot(snap)
    out = tmp_path / "consent.docx"
    native.save(out)

    with zipfile.ZipFile(out) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    # outer fixed-layout table + one-cell box table; the HWPX positioning
    # grid is flattened into the box paragraph rather than becoming a third
    # Word table that would double-count vertical extent.
    assert xml.count("<w:tbl>") == 2
    assert "□ 동의합니다." in xml
    assert "□ 동의하지 않습니다." in xml


def test_docx_native_cell_border_replaces_default_without_duplicate_sides(tmp_path: Path) -> None:
    from lxml import etree
    from pywpdoc._engine.core.snapshot import DocumentSnapshot
    from pywpdoc._engine.docx.snapshot import import_snapshot

    text_fmt = {"font": "Arial", "size_pt": 10.0, "color": "#000000", "ratio": 100, "spacing_percent": 0}
    para_fmt = {"align": "LEFT", "left": 0, "right": 0, "first": 0, "space_before": 0, "space_after": 0, "line_spacing_type": "PERCENT", "line_spacing": 160}
    border = {
        "sides": {
            "leftBorder": {"type": "SOLID", "width": "0.12 mm", "color": "#000000"},
            "rightBorder": {"type": "SOLID", "width": "0.5 mm", "color": "#000000"},
            "topBorder": {"type": "SOLID", "width": "0.12 mm", "color": "#000000"},
            "bottomBorder": {"type": "SOLID", "width": "0.5 mm", "color": "#000000"},
        }
    }
    table = {
        "type": "table", "rows": 1, "cols": 1, "width": 24000, "height": 3000,
        "cells": [{
            "row": 0, "col": 0, "row_span": 1, "col_span": 1,
            "width": 24000, "height": 3000, "vert_align": "TOP",
            "margins": {"left": 510, "right": 510, "top": 141, "bottom": 141},
            "border": border,
            "paragraphs": [{"type": "paragraph", "format": para_fmt,
                            "items": [{"type": "text", "text": "cell", "format": text_fmt}],
                            "layout_lines": []}],
        }],
    }
    snap = DocumentSnapshot(
        source_format="hwpx",
        portable={"page": {"width": 59528, "height": 84186, "left": 5669, "right": 5669, "top": 4252, "bottom": 4252},
                  "blocks": [table]},
    )
    native = import_snapshot(snap)
    out = tmp_path / "borders.docx"
    native.save(out)

    with zipfile.ZipFile(out) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    borders = root.xpath("(.//w:t[text()='cell']/ancestor::w:tc[1]/w:tcPr/w:tcBorders)[1]", namespaces=ns)[0]
    for side in ("top", "left", "bottom", "right"):
        nodes = borders.xpath(f"w:{side}", namespaces=ns)
        assert len(nodes) == 1, side
    bottom = borders.xpath("w:bottom", namespaces=ns)[0]
    assert bottom.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val") == "single"
    # 0.5 mm maps to 11 eighth-points after rounding.
    assert bottom.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sz") == "11"


def test_docx_layout_slot_uses_minimum_row_height_not_exact(tmp_path: Path) -> None:
    """Persisted HWPX line-layout slots are minimum extents, not Word clipping boxes."""
    from lxml import etree
    from pywpdoc._engine.core.snapshot import DocumentSnapshot
    from pywpdoc._engine.docx.snapshot import import_snapshot

    text_fmt = {"font": "Arial", "size_pt": 10.0, "color": "#000000", "ratio": 100, "spacing_percent": 0}
    para_fmt = {"align": "LEFT", "left": 0, "right": 0, "first": 0, "space_before": 0, "space_after": 0, "line_spacing_type": "PERCENT", "line_spacing": 160}
    snap = DocumentSnapshot(
        source_format="hwpx",
        portable={
            "page": {"width": 59528, "height": 84186, "left": 5669, "right": 5669, "top": 4252, "bottom": 4252},
            "blocks": [{
                "type": "paragraph",
                "layout": {"top": 0, "slot_height": 5842},
                "format": para_fmt,
                "items": [{"type": "text", "text": "layout slot", "format": text_fmt}],
                "layout_lines": [],
            }],
        },
    )
    native = import_snapshot(snap)
    out = tmp_path / "layout-slot.docx"
    native.save(out)

    with zipfile.ZipFile(out) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    tr_height = root.xpath("(.//w:trPr/w:trHeight)[1]", namespaces=ns)[0]
    h_rule = tr_height.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hRule")
    assert h_rule == "atLeast"
