from __future__ import annotations

import random
import zipfile
from typing import TYPE_CHECKING

from .model import ElementModel, HP, HC, local_name
from .package import PackageEntryInfo

if TYPE_CHECKING:
    from .document import Document

OPF_NS = "http://www.idpf.org/2007/opf/"
OPF = f"{{{OPF_NS}}}"


def object_id() -> str:
    return str(random.SystemRandom().randrange(1, 2**31 - 1))


def paragraph_id() -> str:
    return object_id()


def distribute_size(total: int, parts: int) -> list[int]:
    if parts <= 0:
        return []
    base, rem = divmod(max(int(total), 0), parts)
    return [base + (1 if i < rem else 0) for i in range(parts)]


def sublist_attrs() -> list[tuple[str, str]]:
    return [
        ("id", ""), ("textDirection", "HORIZONTAL"), ("lineWrap", "BREAK"),
        ("vertAlign", "CENTER"), ("linkListIDRef", "0"),
        ("linkListNextIDRef", "0"), ("textWidth", "0"), ("textHeight", "0"),
        ("hasTextRef", "0"), ("hasNumRef", "0"),
    ]


def paragraph_attrs(*, para_pr_id_ref: str | int = "0", style_id_ref: str | int = "0") -> list[tuple[str, str]]:
    return [
        ("id", paragraph_id()), ("paraPrIDRef", str(para_pr_id_ref)),
        ("styleIDRef", str(style_id_ref)), ("pageBreak", "0"),
        ("columnBreak", "0"), ("merged", "0"),
    ]


def cell_inner_margin() -> list[tuple[str, str]]:
    return [("left", "510"), ("right", "510"), ("top", "141"), ("bottom", "141")]


def zero_margin() -> list[tuple[str, str]]:
    return [("left", "0"), ("right", "0"), ("top", "0"), ("bottom", "0")]


def create_table(
    rows: int,
    cols: int,
    *,
    width: int | None,
    height: int | None,
    border_fill_id_ref: str | int,
) -> ElementModel:
    if rows <= 0 or cols <= 0:
        raise ValueError("rows and cols must be positive integers")
    table_width = int(width if width is not None else cols * 7200)
    table_height = int(height if height is not None else rows * 282)
    border = str(border_fill_id_ref)

    tbl = ElementModel(HP + "tbl", attrs=[
        ("id", object_id()), ("zOrder", "0"), ("numberingType", "TABLE"),
        ("textWrap", "TOP_AND_BOTTOM"), ("textFlow", "BOTH_SIDES"), ("lock", "0"),
        ("dropcapstyle", "None"), ("pageBreak", "CELL"), ("repeatHeader", "0"),
        ("rowCnt", str(rows)), ("colCnt", str(cols)), ("cellSpacing", "0"),
        ("borderFillIDRef", border), ("noAdjust", "0"),
    ])
    tbl.children.extend([
        ElementModel(HP + "sz", attrs=[
            ("width", str(table_width)), ("widthRelTo", "ABSOLUTE"),
            ("height", str(table_height)), ("heightRelTo", "ABSOLUTE"), ("protect", "0"),
        ]),
        ElementModel(HP + "pos", attrs=[
            ("treatAsChar", "1"), ("affectLSpacing", "0"), ("flowWithText", "1"),
            ("allowOverlap", "0"), ("holdAnchorAndSO", "0"), ("vertRelTo", "PARA"),
            ("horzRelTo", "COLUMN"), ("vertAlign", "TOP"), ("horzAlign", "LEFT"),
            ("vertOffset", "0"), ("horzOffset", "0"),
        ]),
        ElementModel(HP + "outMargin", attrs=zero_margin()),
        ElementModel(HP + "inMargin", attrs=cell_inner_margin()),
    ])
    col_widths = distribute_size(table_width, cols)
    row_heights = distribute_size(table_height, rows)
    for r in range(rows):
        tr = ElementModel(HP + "tr")
        for c in range(cols):
            tc = ElementModel(HP + "tc", attrs=[
                ("name", ""), ("header", "0"), ("hasMargin", "0"), ("protect", "0"),
                ("editable", "0"), ("dirty", "0"), ("borderFillIDRef", border),
            ])
            sub = ElementModel(HP + "subList", attrs=sublist_attrs())
            p = ElementModel(HP + "p", attrs=paragraph_attrs())
            run = ElementModel(HP + "run", attrs=[("charPrIDRef", "0")])
            run.children.append(ElementModel(HP + "t", text=""))
            p.children.append(run)
            sub.children.append(p)
            tc.children.extend([
                sub,
                ElementModel(HP + "cellAddr", attrs=[("colAddr", str(c)), ("rowAddr", str(r))]),
                ElementModel(HP + "cellSpan", attrs=[("colSpan", "1"), ("rowSpan", "1")]),
                ElementModel(HP + "cellSz", attrs=[("width", str(col_widths[c])), ("height", str(row_heights[r]))]),
                ElementModel(HP + "cellMargin", attrs=cell_inner_margin()),
            ])
            tr.children.append(tc)
        tbl.children.append(tr)
    return tbl


_IDENTITY = [("e1", "1"), ("e2", "0"), ("e3", "0"), ("e4", "0"), ("e5", "1"), ("e6", "0")]


def _shape_common(parent: ElementModel, width: int, height: int, *, treat_as_char: bool) -> None:
    ident = object_id()
    for k, v in [
        ("id", ident), ("zOrder", "0"), ("numberingType", "NONE"), ("textWrap", "SQUARE"),
        ("textFlow", "BOTH_SIDES"), ("lock", "0"), ("dropcapstyle", "None"),
        ("href", ""), ("groupLevel", "0"), ("instid", ident),
    ]:
        parent.set(k, v)
    parent.children.extend([
        ElementModel(HP + "offset", attrs=[("x", "0"), ("y", "0")]),
        ElementModel(HP + "orgSz", attrs=[("width", str(width)), ("height", str(height))]),
        ElementModel(HP + "curSz", attrs=[("width", str(width)), ("height", str(height))]),
        ElementModel(HP + "flip", attrs=[("horizontal", "0"), ("vertical", "0")]),
        ElementModel(HP + "rotationInfo", attrs=[
            ("angle", "0"), ("centerX", str(width // 2)), ("centerY", str(height // 2)), ("rotateimage", "1")
        ]),
    ])
    rendering = ElementModel(HP + "renderingInfo")
    rendering.children.extend([
        ElementModel(HC + "transMatrix", attrs=list(_IDENTITY)),
        ElementModel(HC + "scaMatrix", attrs=list(_IDENTITY)),
        ElementModel(HC + "rotMatrix", attrs=list(_IDENTITY)),
    ])
    parent.children.append(rendering)
    parent.set("_treatAsChar", "1" if treat_as_char else "0")


def _shape_drawing(parent: ElementModel, *, line_color: str, line_width: str, fill_color: str | None) -> None:
    parent.children.append(ElementModel(HP + "lineShape", attrs=[
        ("color", line_color.upper()), ("width", str(line_width)), ("style", "SOLID"),
        ("endCap", "FLAT"), ("headStyle", "NORMAL"), ("tailStyle", "NORMAL"),
        ("headfill", "1"), ("tailfill", "1"), ("headSz", "SMALL_SMALL"),
        ("tailSz", "SMALL_SMALL"), ("outlineStyle", "NORMAL"), ("alpha", "0"),
    ]))
    if fill_color is not None:
        fill = ElementModel(HC + "fillBrush")
        fill.children.append(ElementModel(HC + "winBrush", attrs=[
            ("faceColor", fill_color.upper()), ("hatchColor", "#FFFFFF"), ("alpha", "0")
        ]))
        parent.children.append(fill)
    parent.children.append(ElementModel(HP + "shadow", attrs=[
        ("type", "NONE"), ("color", "#B2B2B2"), ("offsetX", "0"), ("offsetY", "0"), ("alpha", "0")
    ]))


def _shape_base(parent: ElementModel, width: int, height: int) -> None:
    treat = parent.get("_treatAsChar", "1") == "1"
    parent.remove_attr("_treatAsChar")
    parent.children.extend([
        ElementModel(HP + "sz", attrs=[
            ("width", str(width)), ("height", str(height)), ("widthRelTo", "ABSOLUTE"),
            ("heightRelTo", "ABSOLUTE"), ("protect", "0"),
        ]),
        ElementModel(HP + "pos", attrs=[
            ("treatAsChar", "1" if treat else "0"), ("affectLSpacing", "0"),
            ("flowWithText", "1" if treat else "0"), ("allowOverlap", "0" if treat else "1"),
            ("holdAnchorAndSO", "0"), ("vertRelTo", "PARA"), ("horzRelTo", "COLUMN"),
            ("vertAlign", "TOP"), ("horzAlign", "LEFT"), ("vertOffset", "0"), ("horzOffset", "0"),
        ]),
        ElementModel(HP + "outMargin", attrs=zero_margin()),
    ])


def create_rectangle(
    width: int,
    height: int,
    *,
    line_color: str = "#000000",
    line_width: str = "33",
    fill_color: str | None = None,
    treat_as_char: bool = True,
    text: str | None = None,
    para_pr_id_ref: str | int = "0",
    char_pr_id_ref: str | int = "0",
) -> ElementModel:
    rect = ElementModel(HP + "rect", attrs=[("ratio", "0")])
    _shape_common(rect, int(width), int(height), treat_as_char=treat_as_char)
    _shape_drawing(rect, line_color=line_color, line_width=line_width, fill_color=fill_color)
    if text is not None:
        draw = ElementModel(HP + "drawText", attrs=[("lastWidth", str(width)), ("name", ""), ("editable", "0")])
        sub = ElementModel(HP + "subList", attrs=sublist_attrs())
        p = ElementModel(HP + "p", attrs=paragraph_attrs(para_pr_id_ref=para_pr_id_ref))
        run = ElementModel(HP + "run", attrs=[("charPrIDRef", str(char_pr_id_ref))])
        run.children.append(ElementModel(HP + "t", text=text))
        p.children.append(run)
        sub.children.append(p)
        draw.children.extend([sub, ElementModel(HP + "textMargin", attrs=[("left", "283"), ("right", "283"), ("top", "283"), ("bottom", "283")])])
        rect.children.append(draw)
    rect.children.extend([
        ElementModel(HC + "pt0", attrs=[("x", "0"), ("y", "0")]),
        ElementModel(HC + "pt1", attrs=[("x", str(width)), ("y", "0")]),
        ElementModel(HC + "pt2", attrs=[("x", str(width)), ("y", str(height))]),
        ElementModel(HC + "pt3", attrs=[("x", "0"), ("y", str(height))]),
    ])
    _shape_base(rect, int(width), int(height))
    return rect


def create_picture(binary_item_id_ref: str, width: int, height: int, *, treat_as_char: bool = True) -> ElementModel:
    pic = ElementModel(HP + "pic", attrs=[
        ("textWrap", "SQUARE"), ("textFlow", "BOTH_SIDES"), ("reverse", "0")
    ])
    _shape_common(pic, int(width), int(height), treat_as_char=treat_as_char)
    pic.set("numberingType", "PICTURE")
    rect = ElementModel(HP + "imgRect")
    rect.children.extend([
        ElementModel(HC + "pt0", attrs=[("x", "0"), ("y", "0")]),
        ElementModel(HC + "pt1", attrs=[("x", str(width)), ("y", "0")]),
        ElementModel(HC + "pt2", attrs=[("x", str(width)), ("y", str(height))]),
        ElementModel(HC + "pt3", attrs=[("x", "0"), ("y", str(height))]),
    ])
    pic.children.extend([
        rect,
        ElementModel(HP + "imgClip", attrs=[("left", "0"), ("right", str(width)), ("top", "0"), ("bottom", str(height))]),
        ElementModel(HP + "inMargin", attrs=zero_margin()),
        ElementModel(HP + "imgDim", attrs=[("dimwidth", str(width)), ("dimheight", str(height))]),
        ElementModel(HC + "img", attrs=[
            ("binaryItemIDRef", binary_item_id_ref), ("bright", "0"), ("contrast", "0"),
            ("effect", "REAL_PIC"), ("alpha", "0"),
        ]),
        ElementModel(HP + "effects"),
    ])
    _shape_base(pic, int(width), int(height))
    return pic


_MEDIA_TYPES = {
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "bmp": "image/bmp",
}


def add_binary_image(document: "Document", data: bytes, image_format: str) -> str:
    fmt = image_format.lower().lstrip(".")
    if fmt not in _MEDIA_TYPES:
        raise ValueError(f"unsupported image format: {image_format}")
    manifest = next((n for n in document.content_model.iter() if local_name(n.tag) == "manifest"), None)
    if manifest is None:
        raise ValueError("content.hpf has no manifest")
    used = {n.get("id") for n in manifest.children if local_name(n.tag) == "item"}
    index = 1
    while f"image{index}" in used or f"BinData/image{index}.{fmt}" in document._package.parts:
        index += 1
    item_id = f"image{index}"
    name = f"BinData/{item_id}.{fmt}"
    manifest.children.append(ElementModel(OPF + "item", attrs=[
        ("id", item_id), ("href", name), ("media-type", _MEDIA_TYPES[fmt]), ("isEmbeded", "1")
    ]))
    # Use the section entry's metadata conventions for the new ZIP member.
    ref = document._package.infos.get("Contents/section0.xml")
    date_time = ref.date_time if ref is not None else (2026, 1, 1, 0, 0, 0)
    document._package.set(name, bytes(data), PackageEntryInfo(name, zipfile.ZIP_DEFLATED, date_time))
    return item_id
