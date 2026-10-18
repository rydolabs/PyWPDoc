"""HWPX-owned structural snapshot export/import for Common rebuilds."""
from __future__ import annotations

from typing import Any

from ..core.snapshot import DocumentSnapshot
from ..model import ElementModel, local_name
from ..package import HwpxPackage
from ..document import Document as NativeDocument


def _child(node: ElementModel | None, name: str) -> ElementModel | None:
    if node is None:
        return None
    return next((c for c in node.children if local_name(c.tag) == name), None)


def _int(node: ElementModel | None, name: str, default: int = 0) -> int:
    if node is None:
        return default
    try:
        return int(node.get(name, str(default)) or default)
    except (TypeError, ValueError):
        return default


def _index(root: ElementModel, item_name: str) -> dict[str, ElementModel]:
    out: dict[str, ElementModel] = {}
    for n in root.iter():
        if local_name(n.tag) == item_name and n.get("id") is not None:
            out[str(n.get("id"))] = n
    return out




def _border_defs(header: ElementModel) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for bf in header.iter():
        if local_name(bf.tag) != "borderFill" or bf.get("id") is None:
            continue
        fill = None
        brush = next((n for n in bf.iter() if local_name(n.tag) == "winBrush"), None)
        if brush is not None:
            face = str(brush.get("faceColor", "none") or "none")
            if face.lower() != "none": fill = face
        sides = {}
        for side in ("leftBorder","rightBorder","topBorder","bottomBorder"):
            el = _child(bf, side)
            if el is not None:
                sides[side] = {"type": str(el.get("type","NONE") or "NONE"), "width": str(el.get("width","0.12 mm") or "0.12 mm"), "color": str(el.get("color","#000000") or "#000000")}
        out[str(bf.get("id"))] = {"fill": fill, "sides": sides}
    return out

def _font_names(header: ElementModel) -> dict[str, str]:
    # Prefer HANGUL fontface because the source is predominantly Korean.
    for ff in header.iter():
        if local_name(ff.tag) == "fontface" and ff.get("lang") == "HANGUL":
            return {str(f.get("id")): str(f.get("face", "")) for f in ff.children if local_name(f.tag) == "font"}
    return {}


def _char_format(char_id: str, chars: dict[str, ElementModel], fonts: dict[str, str]) -> dict[str, Any]:
    cp = chars.get(str(char_id))
    if cp is None:
        return {"id": str(char_id)}
    fr = _child(cp, "fontRef")
    ratio = _child(cp, "ratio")
    spacing = _child(cp, "spacing")
    hangul_font_id = "0" if fr is None else str(fr.get("hangul", "0"))
    d: dict[str, Any] = {
        "id": str(char_id),
        "font": fonts.get(hangul_font_id, ""),
        "size_pt": _int(cp, "height", 1000) / 100.0,
        "color": str(cp.get("textColor", "#000000") or "#000000"),
        "ratio": _int(ratio, "hangul", 100),
        "spacing_percent": _int(spacing, "hangul", 0),
        "bold": any(local_name(c.tag) == "bold" for c in cp.children),
        "italic": any(local_name(c.tag) == "italic" for c in cp.children),
        "underline": any(local_name(c.tag) == "underline" and str(c.get("type", "NONE")) != "NONE" for c in cp.children),
        "strike": any(local_name(c.tag) in {"strikeout", "strikeOut"} and str(c.get("shape", "NONE")) != "NONE" for c in cp.children),
    }
    return d


def _para_case(pp: ElementModel | None) -> ElementModel | None:
    if pp is None:
        return None
    switch = _child(pp, "switch")
    if switch is None:
        return pp
    case = _child(switch, "case")
    return case or _child(switch, "default") or pp


def _para_format(para_id: str, paras: dict[str, ElementModel]) -> dict[str, Any]:
    pp = paras.get(str(para_id))
    if pp is None:
        return {"id": str(para_id)}
    align = _child(pp, "align")
    case = _para_case(pp)
    margin = _child(case, "margin") if case is not None else None
    line = _child(case, "lineSpacing") if case is not None else None
    def mv(name: str) -> int:
        return _int(_child(margin, name), "value", 0) if margin is not None else 0
    return {
        "id": str(para_id),
        "align": "JUSTIFY" if align is None else str(align.get("horizontal", "JUSTIFY") or "JUSTIFY"),
        "left": mv("left"), "right": mv("right"), "first": mv("intent"),
        "space_before": mv("prev"), "space_after": mv("next"),
        "line_spacing_type": "PERCENT" if line is None else str(line.get("type", "PERCENT") or "PERCENT"),
        "line_spacing": 160 if line is None else _int(line, "value", 160),
    }


def _text_of_t(t: ElementModel) -> str:
    parts = [t.text or ""]
    atom = {"tab": "\t", "lineBreak": "\n", "nbSpace": "\u00a0", "fwSpace": "\u3000"}
    for c in t.children:
        parts.append(atom.get(local_name(c.tag), "")); parts.append(c.tail or "")
    return "".join(parts)


def _run_items(run: ElementModel, ctx: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    char_id = str(run.get("charPrIDRef", "0") or "0")
    fmt = _char_format(char_id, ctx["chars"], ctx["fonts"])
    for c in run.children:
        name = local_name(c.tag)
        if name == "t":
            out.append({"type": "text", "text": _text_of_t(c), "format": fmt})
        elif name == "pic":
            out.append(_picture(c, ctx))
        elif name == "tbl":
            out.append(_table(c, ctx))
        elif name == "rect":
            out.append(_rect(c, ctx))
    if not out:
        out.append({"type": "text", "text": "", "format": fmt})
    return out


def _paragraph(p: ElementModel, ctx: dict[str, Any]) -> dict[str, Any]:
    para_id = str(p.get("paraPrIDRef", "0") or "0")
    items: list[dict[str, Any]] = []
    for c in p.children:
        if local_name(c.tag) == "run":
            items.extend(_run_items(c, ctx))
    lsa = _child(p, "linesegarray")
    lines = [] if lsa is None else [x for x in lsa.children if local_name(x.tag) == "lineseg"]
    layout_lines = [{"textpos": _int(x, "textpos", 0), "top": _int(x, "vertpos", 0), "height": _int(x, "vertsize", 0), "spacing": _int(x, "spacing", 0), "horz": _int(x, "horzpos", 0), "width": _int(x, "horzsize", 0)} for x in lines]
    return {"type": "paragraph", "format": _para_format(para_id, ctx["paras"]), "items": items, "layout_lines": layout_lines}


def _picture(pic: ElementModel, ctx: dict[str, Any]) -> dict[str, Any]:
    sz = _child(pic, "sz"); pos = _child(pic, "pos"); img = _child(pic, "img")
    item_id = "" if img is None else str(img.get("binaryItemIDRef", "") or "")
    media = ctx["media"].get(item_id, {})
    return {
        "type": "picture", "width": _int(sz, "width", 0), "height": _int(sz, "height", 0),
        "treat_as_char": pos is None or pos.get("treatAsChar", "1") == "1",
        "data": media.get("data"), "format": media.get("format"), "item_id": item_id,
    }


def _cell(tc: ElementModel, ctx: dict[str, Any]) -> dict[str, Any]:
    addr = _child(tc, "cellAddr"); span = _child(tc, "cellSpan"); sz = _child(tc, "cellSz"); sub = _child(tc, "subList")
    paras = [] if sub is None else [_paragraph(p, ctx) for p in sub.children if local_name(p.tag) == "p"]
    cm = _child(tc, "cellMargin")
    return {
        "row": _int(addr, "rowAddr", 0), "col": _int(addr, "colAddr", 0),
        "row_span": _int(span, "rowSpan", 1), "col_span": _int(span, "colSpan", 1),
        "width": _int(sz, "width", 0), "height": _int(sz, "height", 0),
        "vert_align": "CENTER" if sub is None else str(sub.get("vertAlign", "TOP") or "TOP"),
        "border_ref": str(tc.get("borderFillIDRef", "0") or "0"),
        "border": ctx.get("borders", {}).get(str(tc.get("borderFillIDRef", "0") or "0"), {}),
        "margins": {"left": _int(cm, "left", 510), "right": _int(cm, "right", 510), "top": _int(cm, "top", 141), "bottom": _int(cm, "bottom", 141)},
        "paragraphs": paras,
    }


def _table(tbl: ElementModel, ctx: dict[str, Any]) -> dict[str, Any]:
    sz = _child(tbl, "sz"); pos = _child(tbl, "pos")
    cells: list[dict[str, Any]] = []
    for tr in tbl.children:
        if local_name(tr.tag) != "tr": continue
        for tc in tr.children:
            if local_name(tc.tag) == "tc": cells.append(_cell(tc, ctx))
    return {
        "type": "table", "rows": _int(tbl, "rowCnt", 1), "cols": _int(tbl, "colCnt", 1),
        "width": _int(sz, "width", 0), "height": _int(sz, "height", 0),
        "treat_as_char": pos is None or pos.get("treatAsChar", "1") == "1",
        "page_break": str(tbl.get("pageBreak", "CELL") or "CELL"),
        "repeat_header": str(tbl.get("repeatHeader", "0") or "0") == "1",
        "border_ref": str(tbl.get("borderFillIDRef", "0") or "0"), "cells": cells,
    }


def _rect(rect: ElementModel, ctx: dict[str, Any]) -> dict[str, Any]:
    sz = _child(rect, "sz"); pos = _child(rect, "pos"); line = _child(rect, "lineShape"); draw = _child(rect, "drawText"); sub = _child(draw, "subList")
    paragraphs = [] if sub is None else [_paragraph(p, ctx) for p in sub.children if local_name(p.tag) == "p"]
    return {
        "type": "box", "width": _int(sz, "width", 0), "height": _int(sz, "height", 0),
        "treat_as_char": pos is None or pos.get("treatAsChar", "1") == "1",
        "flow_with_text": pos is None or pos.get("flowWithText", "1") == "1",
        "vert_offset": _int(pos, "vertOffset", 0), "horz_offset": _int(pos, "horzOffset", 0),
        "line_color": "#000000" if line is None else str(line.get("color", "#000000") or "#000000"),
        "line_width": "0.12 mm" if line is None else str(line.get("width", "0.12 mm") or "0.12 mm"),
        "paragraphs": paragraphs,
    }


def _media(native: NativeDocument) -> dict[str, dict[str, Any]]:
    # id -> binary payload from OPF manifest
    items: dict[str, dict[str, Any]] = {}
    content = native.content_model
    for n in content.iter():
        if local_name(n.tag) != "item": continue
        item_id = str(n.get("id", "") or ""); href = str(n.get("href", "") or ""); mt = str(n.get("media-type", "") or "")
        if item_id and href and href in native._package.parts and mt.startswith("image/"):
            items[item_id] = {"data": native._package.parts[href], "format": mt.split("/",1)[1], "href": href}
    return items


def export_snapshot(native: NativeDocument, *, preserve_layout: bool = True) -> DocumentSnapshot:
    # Make package bytes current without introducing any cross-format logic.
    native._prepare_for_save()
    header = native.header_model
    chars = _index(header, "charPr"); paras = _index(header, "paraPr"); fonts = _font_names(header)
    ctx = {"chars": chars, "paras": paras, "fonts": fonts, "media": _media(native), "borders": _border_defs(header)}
    sec = native.section_models[0]
    # page geometry
    secpr = next((n for n in sec.iter() if local_name(n.tag) == "secPr"), None)
    page = _child(secpr, "pagePr"); margin = _child(page, "margin")
    portable: dict[str, Any] = {
        "page": {
            "width": _int(page, "width", 59528), "height": _int(page, "height", 84186),
            "left": _int(margin, "left", 0), "right": _int(margin, "right", 0),
            "top": _int(margin, "top", 0), "bottom": _int(margin, "bottom", 0),
            "header": _int(margin, "header", 0), "footer": _int(margin, "footer", 0),
        },
        "blocks": [],
    }
    top_paragraphs = [p for p in sec.children if local_name(p.tag) == "p"]
    tops: list[int] = []
    for p in top_paragraphs:
        lsa = _child(p, "linesegarray")
        lines = [] if lsa is None else [x for x in lsa.children if local_name(x.tag) == "lineseg"]
        tops.append(_int(lines[0], "vertpos", 0) if lines else (tops[-1] if tops else 0))
    page_body = max(0, portable["page"]["height"] - portable["page"]["top"] - portable["page"]["bottom"] - portable["page"]["header"] - portable["page"]["footer"] )
    for idx, p in enumerate(top_paragraphs):
        para = _paragraph(p, ctx)
        lsa = _child(p, "linesegarray")
        lines = [] if lsa is None else [x for x in lsa.children if local_name(x.tag) == "lineseg"]
        top = tops[idx]
        if idx + 1 < len(tops):
            slot_height = max(0, tops[idx + 1] - top)
        elif lines:
            last = lines[-1]
            slot_height = max(0, _int(last, "vertpos", top) + _int(last, "vertsize", 0) - top)
        else:
            slot_height = max(0, page_body - top)
        layout = {"top": top, "slot_height": slot_height}
        visible = [it for it in para["items"] if it.get("type") != "text" or it.get("text")]
        if visible and all(it.get("type") == "text" for it in visible):
            para["layout"] = layout
            portable["blocks"].append(para)
        elif visible:
            objs = [it for it in para["items"] if it.get("type") in {"table", "box", "picture"}]
            for pos, it in enumerate(objs):
                it["layout"] = layout if pos == 0 else {"top": top, "slot_height": 0}
                portable["blocks"].append(it)
        else:
            para["layout"] = layout
            portable["blocks"].append(para)
    payload = {"hwpx_package": native._package.to_bytes()} if preserve_layout else {}
    return DocumentSnapshot(source_format="hwpx", portable=portable, native_payload=payload)


def import_snapshot(snapshot: DocumentSnapshot, *, preserve_layout: bool = True) -> NativeDocument:
    raw = snapshot.native_payload.get("hwpx_package") if preserve_layout else None
    if snapshot.source_format == "hwpx" and isinstance(raw, (bytes, bytearray)):
        return NativeDocument(HwpxPackage(bytes(raw)))
    raise ValueError("HWPX snapshot import currently requires an HWPX native payload")


__all__ = ["export_snapshot", "import_snapshot"]
