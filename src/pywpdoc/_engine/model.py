from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, TYPE_CHECKING
from lxml import etree
import re

from .errors import HwpxValueError, HwpxUnsupportedError

if TYPE_CHECKING:
    from .document import Document

HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HH_NS = "http://www.hancom.co.kr/hwpml/2011/head"
HS_NS = "http://www.hancom.co.kr/hwpml/2011/section"
HC_NS = "http://www.hancom.co.kr/hwpml/2011/core"

HP = f"{{{HP_NS}}}"
HH = f"{{{HH_NS}}}"
HS = f"{{{HS_NS}}}"
HC = f"{{{HC_NS}}}"


def local_name(tag: Any) -> str:
    if not isinstance(tag, str):
        return ""
    return etree.QName(tag).localname if tag.startswith("{") else tag


_HYPERLINK_FIELD_ID = "627600491"
_HYPERLINK_COMMAND_TAIL = re.compile(r";\d+;\d+;\d+;?$")
_HYPERLINK_UNESCAPE = re.compile(r"\\(.)")



_INLINE_TEXT_ATOMS = {
    "tab": "\t",
    "lineBreak": "\n",
    "nbSpace": "\u00a0",
    "fwSpace": "\u3000",
    "hyphen": "-",
}


def _text_element_string(node: "ElementModel") -> str:
    """Return one hp:t as Python text, including mixed-content atoms."""
    parts = [node.text or ""]
    for child in node.children:
        parts.append(_INLINE_TEXT_ATOMS.get(local_name(child.tag), ""))
        parts.append(child.tail or "")
    return "".join(parts)


def _mixed_text_element(value: str | None) -> "ElementModel":
    """Build one hp:t using Hancom-native mixed content for tabs/breaks."""
    text = "" if value is None else str(value).replace("\r\n", "\n").replace("\r", "\n")
    node = ElementModel(HP + "t", text="")
    markers = {"\t": "tab", "\n": "lineBreak", "\u00a0": "nbSpace", "\u3000": "fwSpace"}
    pending: list[str] = []
    last: ElementModel | None = None

    def flush() -> None:
        nonlocal pending, last
        payload = "".join(pending)
        if last is None:
            node.text = payload
        else:
            last.tail = payload
        pending = []

    for ch in text:
        name = markers.get(ch)
        if name is None:
            pending.append(ch)
            continue
        flush()
        last = ElementModel(HP + name)
        node.children.append(last)
    flush()
    return node

def _escape_hyperlink_target(text: str) -> str:
    return "".join("\\" + ch if ch in ":?;#" else ch for ch in text)


def _hyperlink_parameters(url: str) -> list[tuple[str, str, str]]:
    if url.startswith("#"):
        command, path, category = f"?{_escape_hyperlink_target(url[1:])};0;0;0;", None, "HWPHYPERLINK_TYPE_HWP"
    elif url.lower().startswith("mailto:"):
        command, path, category = f"{url};2;0;0", url, "HWPHYPERLINK_TYPE_EMAIL"
    else:
        command, path, category = f"{_escape_hyperlink_target(url)};1;0;0;", url, "HWPHYPERLINK_TYPE_URL"
    params = [("integerParam", "Prop", "0"), ("stringParam", "Command", command)]
    if path is not None:
        params.append(("stringParam", "Path", path))
    params.extend([
        ("stringParam", "Category", category),
        ("stringParam", "TargetType", "HWPHYPERLINK_TARGET_BOOKMARK"),
        ("stringParam", "DocOpenType", "HWPHYPERLINK_JUMP_CURRENTTAB"),
    ])
    return params


def _hyperlink_target(field_begin: "ElementModel") -> str:
    command: str | None = None
    holder = next((c for c in field_begin.children if local_name(c.tag) == "parameters"), None)
    if holder is not None:
        for param in holder.children:
            name = param.get("name")
            if name == "Path" and (param.text or "").strip():
                return param.text or ""
            if name == "Command" and param.text:
                command = param.text
    if command:
        head = _HYPERLINK_COMMAND_TAIL.sub("", command).split("|", 1)[0]
        head = _HYPERLINK_UNESCAPE.sub(r"\1", head)
        if head.startswith("?") and not head.startswith("?#"):
            return "#" + head[1:]
        return head
    return field_begin.get("name", "") or ""


_TYPED_KINDS = {
    "sec": "section",
    "p": "paragraph",
    "run": "run",
    "tbl": "table",
    "tr": "row",
    "tc": "cell",
    "pic": "picture",
    "rect": "rectangle",
    "footNote": "footnote",
    "endNote": "endnote",
    "header": "header",
    "footer": "footer",
    "bookmark": "bookmark",
    "fieldBegin": "field",
    "fieldEnd": "field",
    "t": "text",
}


@dataclass
class ElementModel:
    """Lossless XML-backed IR node.

    Typed proxies expose the commonly edited HWPX concepts while every unknown
    attribute, child, ordering detail, and cache node remains here unchanged.
    """

    tag: str
    attrs: list[tuple[str, str]] = field(default_factory=list)
    text: str | None = None
    tail: str | None = None
    nsmap: list[tuple[str | None, str]] | None = None
    children: list["ElementModel"] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return _TYPED_KINDS.get(local_name(self.tag), "oxml")

    @classmethod
    def from_element(cls, element: etree._Element, *, root: bool = False) -> "ElementModel":
        return cls(
            tag=element.tag,
            attrs=list(element.attrib.items()),
            text=element.text,
            tail=element.tail,
            nsmap=list(element.nsmap.items()) if root else None,
            children=[cls.from_element(c) for c in element],
        )

    def to_element(self, *, root: bool = False) -> etree._Element:
        nsmap = dict(self.nsmap) if root and self.nsmap else None
        element = etree.Element(self.tag, nsmap=nsmap)
        for key, value in self.attrs:
            element.set(key, value)
        element.text = self.text
        for child in self.children:
            element.append(child.to_element())
        element.tail = self.tail
        return element

    def get(self, name: str, default: str | None = None) -> str | None:
        for key, value in self.attrs:
            if key == name:
                return value
        return default

    def set(self, name: str, value: str) -> None:
        for i, (key, _) in enumerate(self.attrs):
            if key == name:
                self.attrs[i] = (key, value)
                return
        self.attrs.append((name, value))

    def remove_attr(self, name: str) -> None:
        self.attrs[:] = [(k, v) for k, v in self.attrs if k != name]

    def find_children(self, name: str) -> list["ElementModel"]:
        return [c for c in self.children if local_name(c.tag) == name]

    def iter(self) -> Iterator["ElementModel"]:
        yield self
        for child in self.children:
            yield from child.iter()

    def to_dict(self) -> dict[str, Any]:
        return {
            "tag": self.tag,
            "attrs": [list(item) for item in self.attrs],
            "text": self.text,
            "tail": self.tail,
            "nsmap": None if self.nsmap is None else [[k, v] for k, v in self.nsmap],
            "children": [c.to_dict() for c in self.children],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ElementModel":
        return cls(
            tag=data["tag"],
            attrs=[tuple(x) for x in data.get("attrs", [])],
            text=data.get("text"),
            tail=data.get("tail"),
            nsmap=None if data.get("nsmap") is None else [tuple(x) for x in data["nsmap"]],
            children=[cls.from_dict(c) for c in data.get("children", [])],
        )


class NodeProxy:
    def __init__(self, model: ElementModel, document: "Document | None" = None):
        self._model = model
        self._document = document

    @property
    def element_model(self) -> ElementModel:
        return self._model

    @property
    def document(self) -> "Document | None":
        return self._document

    @property
    def kind(self) -> str:
        return self._model.kind


class PageSetup:
    def __init__(self, section: "Section"):
        self.section = section

    def _page_pr(self) -> ElementModel:
        sec_pr = next((n for n in self.section.element_model.iter() if local_name(n.tag) == "secPr"), None)
        if sec_pr is None:
            raise ValueError("section has no secPr")
        page = next((c for c in sec_pr.children if local_name(c.tag) == "pagePr"), None)
        if page is None:
            page = ElementModel(HP + "pagePr", attrs=[("landscape","WIDELY"),("width","59528"),("height","84186"),("gutterType","LEFT_ONLY")])
            page.children.append(ElementModel(HP + "margin", attrs=[("header","0"),("footer","0"),("gutter","0"),("left","0"),("right","0"),("top","0"),("bottom","0")]))
            sec_pr.children.append(page)
        return page

    def _margin(self) -> ElementModel:
        page = self._page_pr()
        margin = next((c for c in page.children if local_name(c.tag) == "margin"), None)
        if margin is None:
            margin = ElementModel(HP + "margin", attrs=[("header","0"),("footer","0"),("gutter","0"),("left","0"),("right","0"),("top","0"),("bottom","0")])
            page.children.append(margin)
        return margin

    @property
    def width(self):
        from .shared import HwpUnit
        return HwpUnit(int(self._page_pr().get("width", "0") or 0))

    @width.setter
    def width(self, value: int) -> None:
        page = self._page_pr()
        desired = str(int(value))
        if page.get("width") != desired:
            page.set("width", desired)
            from ._hwpx_section import invalidate_layout_cache
            invalidate_layout_cache(self.section)

    @property
    def height(self):
        from .shared import HwpUnit
        return HwpUnit(int(self._page_pr().get("height", "0") or 0))

    @height.setter
    def height(self, value: int) -> None:
        page = self._page_pr()
        desired = str(int(value))
        if page.get("height") != desired:
            page.set("height", desired)
            from ._hwpx_section import invalidate_layout_cache
            invalidate_layout_cache(self.section)

    @property
    def landscape(self) -> str | None:
        return self._page_pr().get("landscape")

    @landscape.setter
    def landscape(self, value: str) -> None:
        page = self._page_pr()
        desired = str(value).upper()
        if page.get("landscape") != desired:
            page.set("landscape", desired)
            from ._hwpx_section import invalidate_layout_cache
            invalidate_layout_cache(self.section)

    def _get_margin(self, name: str):
        from .shared import HwpUnit
        return HwpUnit(int(self._margin().get(name, "0") or 0))

    def _set_margin(self, name: str, value: int) -> None:
        margin = self._margin()
        desired = str(int(value))
        if margin.get(name) != desired:
            margin.set(name, desired)
            from ._hwpx_section import invalidate_layout_cache
            invalidate_layout_cache(self.section)

    left_margin = property(lambda self: self._get_margin("left"), lambda self, v: self._set_margin("left", v))
    right_margin = property(lambda self: self._get_margin("right"), lambda self, v: self._set_margin("right", v))
    top_margin = property(lambda self: self._get_margin("top"), lambda self, v: self._set_margin("top", v))
    bottom_margin = property(lambda self: self._get_margin("bottom"), lambda self, v: self._set_margin("bottom", v))
    header_distance = property(lambda self: self._get_margin("header"), lambda self, v: self._set_margin("header", v))
    footer_distance = property(lambda self: self._get_margin("footer"), lambda self, v: self._set_margin("footer", v))
    gutter = property(lambda self: self._get_margin("gutter"), lambda self, v: self._set_margin("gutter", v))


class HeaderFooter(NodeProxy):
    def __init__(self, model: ElementModel, section: "Section", kind: str):
        super().__init__(model, section.document)
        self.section = section
        self.story_kind = kind

    @property
    def id(self) -> str | None:
        return self._model.get("id")

    @property
    def apply_page_type(self) -> str:
        return self._model.get("applyPageType", "BOTH") or "BOTH"

    def _ensure_sublist(self) -> ElementModel:
        from .authoring import sublist_attrs
        sub = next((c for c in self._model.children if local_name(c.tag) == "subList"), None)
        if sub is None:
            attrs = dict(sublist_attrs())
            attrs.update(dict(self.section._story_sublist_attrs(self.story_kind)))
            sub = ElementModel(HP + "subList", attrs=list(attrs.items()))
            self._model.children.append(sub)
        return sub

    @property
    def paragraphs(self) -> list["Paragraph"]:
        sub = next((c for c in self._model.children if local_name(c.tag) == "subList"), None)
        if sub is None:
            return []
        return [Paragraph(p, self.document) for p in sub.children if local_name(p.tag) == "p"]

    @property
    def tables(self) -> list["Table"]:
        result: list[Table] = []
        sub = next((c for c in self._model.children if local_name(c.tag) == "subList"), None)
        if sub is None:
            return result
        for p in sub.children:
            if local_name(p.tag) != "p":
                continue
            for run in p.children:
                if local_name(run.tag) != "run":
                    continue
                for child in run.children:
                    if local_name(child.tag) == "tbl":
                        result.append(Table(child, self.document))
        return result

    def iter_inner_content(self):
        """Yield header/footer Paragraph and Table blocks in story order."""
        sub = next((c for c in self._model.children if local_name(c.tag) == "subList"), None)
        if sub is None:
            return
        for p_model in sub.children:
            if local_name(p_model.tag) != "p":
                continue
            paragraph = Paragraph(p_model, self.document)
            direct_tables = [
                child
                for run in p_model.children if local_name(run.tag) == "run"
                for child in run.children if local_name(child.tag) == "tbl"
            ]
            non_table_content = False
            for run in p_model.children:
                if local_name(run.tag) != "run":
                    continue
                for child in run.children:
                    lname = local_name(child.tag)
                    if lname == "tbl":
                        continue
                    if lname == "t" and not _text_element_string(child):
                        continue
                    non_table_content = True
            if direct_tables and not paragraph.text and not non_table_content:
                for table in direct_tables:
                    yield Table(table, self.document)
            else:
                yield paragraph

    @property
    def text(self) -> str:
        from ._hwpx_story import paragraph_text
        return paragraph_text(self)

    @property
    def all_text(self) -> str:
        """Format-level text including nested table cells (expert escape hatch)."""
        return "".join(node.text or "" for node in self._model.iter() if local_name(node.tag) == "t")

    @text.setter
    def text(self, value: str) -> None:
        self.section._set_story_text(self.story_kind, self.apply_page_type, str(value))

    def clear_content(self) -> None:
        self._model.children[:] = [c for c in self._model.children if local_name(c.tag) != "subList"]
        style_ref, para_ref, char_ref = self.section._story_style_refs(self.story_kind)
        self.add_paragraph("", para_pr_id_ref=para_ref, style_id_ref=style_ref, char_pr_id_ref=char_ref)

    def add_paragraph(
        self,
        text: str = "",
        style=None,
        *,
        para_pr_id_ref: str | int = "0",
        style_id_ref: str | int = "0",
        char_pr_id_ref: str | int = "0",
    ) -> "Paragraph":
        from .authoring import paragraph_attrs
        sub = self._ensure_sublist()
        p = ElementModel(
            HP + "p",
            attrs=paragraph_attrs(para_pr_id_ref=para_pr_id_ref, style_id_ref=style_id_ref),
        )
        paragraph = Paragraph(p, self.document)
        paragraph.add_run(text, char_pr_id_ref=char_pr_id_ref)
        if style is not None:
            paragraph.style = style
        sub.children.append(p)
        from ._hwpx_story import enable_auto_story_height
        enable_auto_story_height(self)
        return paragraph

    def add_table(
        self, rows: int, cols: int, style=None, *, width: int | None = None,
        height: int | None = None, border_fill_id_ref: str | int | None = None,
    ) -> "Table":
        from ._hwpx_story import normalize_story_table
        target_width = self.section.content_width if width is None else int(width)
        paragraph = self.add_paragraph("")
        table = paragraph.add_table(
            rows, cols, width=target_width, height=height, border_fill_id_ref=border_fill_id_ref
        )
        if style is not None:
            table.style = style
        normalize_story_table(table)
        return table

    def _ensure_content_paragraph(self) -> "Paragraph":
        paragraphs = self.paragraphs
        if paragraphs:
            return paragraphs[0]
        style_ref, para_ref, char_ref = self.section._story_style_refs(self.story_kind)
        return self.add_paragraph(
            "", para_pr_id_ref=para_ref, style_id_ref=style_ref, char_pr_id_ref=char_ref
        )

    def add_run(
        self,
        text: str,
        *,
        paragraph: "Paragraph | None" = None,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        color: str | None = None,
        font: str | None = None,
        size: int | float | None = None,
    ) -> "Run":
        target = paragraph or self._ensure_content_paragraph()
        runs = target.runs
        char_ref: str | int = (runs[-1].char_pr_id_ref or "0") if runs else "0"
        if self.document is not None and any((bold, italic, underline, color, font, size)):
            char_ref = self.document.styles.ensure_run(
                base_char_pr_id=char_ref,
                bold=bold if bold else None,
                italic=italic if italic else None,
                underline=underline if underline else None,
                color=color,
                font=font,
                size=size,
            )
        from ._hwpx_story import enable_auto_story_height
        enable_auto_story_height(self)
        return target.add_run(text, char_pr_id_ref=char_ref)

    def _add_cached_field(self, field_type: str, cached_text: str, params: list[tuple[str,str,str]], *, paragraph: "Paragraph | None" = None) -> ElementModel:
        from .authoring import object_id
        target = paragraph or self._ensure_content_paragraph()
        field_id=object_id(); control_ids={"DATE":"%dte","PATH":"%pat"}; field_ref=str(int.from_bytes(control_ids[field_type].encode("ascii"),"big"))
        runs = target.runs
        char_ref = (runs[-1].char_pr_id_ref or "0") if runs else "0"
        run=ElementModel(HP+"run", attrs=[("charPrIDRef", char_ref)])
        bc=ElementModel(HP+"ctrl"); fb=ElementModel(HP+"fieldBegin", attrs=[("id",field_id),("type",field_type),("name",""),("editable","0"),("dirty","0"),("zorder","-1"),("fieldid",field_ref),("metaTag","")])
        holder=ElementModel(HP+"parameters", attrs=[("cnt",str(len(params))),("name","")])
        for kind,name,value in params: holder.children.append(ElementModel(HP+kind, attrs=[("name",name)], text=value))
        fb.children.append(holder); bc.children.append(fb); run.children.extend([bc,ElementModel(HP+"t",text=cached_text)])
        ec=ElementModel(HP+"ctrl"); ec.children.append(ElementModel(HP+"fieldEnd", attrs=[("beginIDRef",field_id),("fieldid",field_ref)])); run.children.append(ec)
        target._insert_runs_before_layout_cache([run])
        from ._hwpx_story import enable_auto_story_height
        enable_auto_story_height(self)
        return fb

    def add_date_field(self, cached_text: str, *, paragraph: "Paragraph | None" = None, date_format: str = "YYYY년 M월 D일", date_nation: str = "KOR") -> ElementModel:
        if date_format != "YYYY년 M월 D일": raise ValueError("only the observed YYYY년 M월 D일 format is supported")
        return self._add_cached_field("DATE", str(cached_text), [("integerParam","Prop","8"),("stringParam","Command",":1년 2월 3일"),("stringParam","DateNation",date_nation),("stringParam","DateFormat",date_format)], paragraph=paragraph)

    def add_path_field(self, cached_text: str, *, paragraph: "Paragraph | None" = None) -> ElementModel:
        return self._add_cached_field("PATH", str(cached_text), [("integerParam","Prop","8"),("stringParam","Command","$F"),("stringParam","Format","$F")], paragraph=paragraph)

    def add_page_number_field(
        self,
        *,
        paragraph: "Paragraph | None" = None,
        position: str = "BOTTOM_CENTER",
        format_type: str = "DIGIT",
    ) -> ElementModel:
        """Append Hancom's page-number control to this story."""
        target = paragraph or self._ensure_content_paragraph()
        fmt = str(format_type).strip().upper()
        allowed = {
            "DIGIT", "CIRCLED_DIGIT", "ROMAN_CAPITAL", "ROMAN_SMALL",
            "LATIN_CAPITAL", "LATIN_SMALL", "HANGUL_SYLLABLE", "HANGUL_JAMO",
            "IDEOGRAPH",
        }
        if fmt not in allowed:
            raise ValueError(f"unsupported page number format: {format_type}")

        auto_run = ElementModel(HP + "run", attrs=[("charPrIDRef", "0")])
        auto_ctrl = ElementModel(HP + "ctrl")
        auto_num = ElementModel(HP + "autoNum", attrs=[("num", "1"), ("numType", "PAGE")])
        auto_num.children.append(ElementModel(HP + "autoNumFormat", attrs=[
            ("type", fmt), ("userChar", ""), ("prefixChar", ""),
            ("suffixChar", ""), ("supscript", "0"),
        ]))
        auto_ctrl.children.append(auto_num)
        auto_run.children.append(auto_ctrl)

        page_run = ElementModel(HP + "run", attrs=[("charPrIDRef", "0")])
        page_ctrl = ElementModel(HP + "ctrl")
        page = ElementModel(HP + "pageNum", attrs=[
            ("pos", str(position).upper()), ("formatType", fmt), ("sideChar", "-"),
        ])
        page_ctrl.children.append(page)
        page_run.children.append(page_ctrl)

        # runs belong before layout caches
        insert_at = len(target.element_model.children)
        for i, child in enumerate(target.element_model.children):
            if local_name(child.tag) == "linesegarray":
                insert_at = i
                break
        target.element_model.children[insert_at:insert_at] = [auto_run, page_run]
        return page

    def add_page_total_field(
        self,
        *,
        paragraph: "Paragraph | None" = None,
        position: str = "BOTTOM_CENTER",
        format_type: str = "DIGIT",
        separator: str = "/",
    ) -> ElementModel:
        """Append ``current/total`` page numbering in Hancom's native shape."""
        target = paragraph or self._ensure_content_paragraph()
        page_num = self.add_page_number_field(
            paragraph=target, position=position, format_type=format_type
        )
        fmt = str(format_type).strip().upper()
        runs = target.runs
        char_ref = (runs[-1].char_pr_id_ref or "0") if runs else "0"
        target.add_run(str(separator), char_pr_id_ref=char_ref)
        total_run = ElementModel(HP + "run", attrs=[("charPrIDRef", str(char_ref))])
        total_ctrl = ElementModel(HP + "ctrl")
        total_num = ElementModel(HP + "autoNum", attrs=[("num", "1"), ("numType", "TOTAL_PAGE")])
        total_num.children.append(ElementModel(HP + "autoNumFormat", attrs=[
            ("type", fmt), ("userChar", ""), ("prefixChar", ""),
            ("suffixChar", ""), ("supscript", "0"),
        ]))
        total_ctrl.children.append(total_num)
        total_run.children.append(total_ctrl)
        insert_at = len(target.element_model.children)
        for i, child in enumerate(target.element_model.children):
            if local_name(child.tag) == "linesegarray":
                insert_at = i
                break
        target.element_model.children.insert(insert_at, total_run)
        return page_num


class Section(NodeProxy):
    @property
    def page_setup(self) -> PageSetup:
        return PageSetup(self)

    @property
    def content_width(self) -> int:
        from ._hwpx_section import content_width
        return content_width(self)

    def _story_style_refs(self, kind: str) -> tuple[str, str, str]:
        from ._hwpx_section import story_style_refs
        return story_style_refs(self, kind)

    @property
    def paragraphs(self) -> list["Paragraph"]:
        return [Paragraph(p, self.document) for p in self.element_model.children if local_name(p.tag) == "p"]

    def add_paragraph(
        self,
        text: str = "",
        style=None,
        *,
        para_pr_id_ref: str | int = "0",
        style_id_ref: str | int = "0",
        char_pr_id_ref: str | int = "0",
    ) -> "Paragraph":
        if self.document is None:
            raise RuntimeError("section is not attached to a document")
        return self.document.add_paragraph(
            text,
            style=style,
            section=self,
            para_pr_id_ref=para_pr_id_ref,
            style_id_ref=style_id_ref,
            char_pr_id_ref=char_pr_id_ref,
        )

    def _sec_pr(self) -> ElementModel:
        sec_pr = next((n for n in self.element_model.iter() if local_name(n.tag) == "secPr"), None)
        if sec_pr is not None:
            return sec_pr
        from .authoring import paragraph_attrs
        paragraphs = [c for c in self.element_model.children if local_name(c.tag) == "p"]
        if paragraphs:
            p = paragraphs[0]
        else:
            p = ElementModel(HP + "p", attrs=paragraph_attrs())
            self.element_model.children.insert(0, p)
        run = next((c for c in p.children if local_name(c.tag) == "run"), None)
        if run is None:
            run = ElementModel(HP + "run", attrs=[("charPrIDRef", "0")])
            p.children.insert(0, run)
        sec_pr = ElementModel(HP + "secPr")
        run.children.insert(0, sec_pr)
        return sec_pr

    def _first_run(self) -> ElementModel:
        from .authoring import paragraph_attrs
        p = next((c for c in self.element_model.children if local_name(c.tag) == "p"), None)
        if p is None:
            p = ElementModel(HP + "p", attrs=paragraph_attrs())
            self.element_model.children.insert(0, p)
        run = next((c for c in p.children if local_name(c.tag) == "run"), None)
        if run is None:
            run = ElementModel(HP + "run", attrs=[("charPrIDRef", "0")])
            p.children.insert(0, run)
        return run

    def _logical_story(self, kind: str, page_type: str) -> ElementModel | None:
        sec_pr = self._sec_pr()
        return next((c for c in sec_pr.children if local_name(c.tag) == kind and (c.get("applyPageType", "BOTH") or "BOTH") == page_type), None)

    def _control_story(self, kind: str, page_type: str, native_id: str | None = None) -> ElementModel | None:
        for node in self.element_model.iter():
            if local_name(node.tag) != "ctrl":
                continue
            for child in node.children:
                if local_name(child.tag) != kind:
                    continue
                if (child.get("applyPageType", "BOTH") or "BOTH") != page_type:
                    continue
                if native_id is not None and child.get("id") != native_id:
                    continue
                return child
        return None

    def _story_sublist_attrs(self, kind: str) -> list[tuple[str, str]]:
        from ._hwpx_section import story_sublist_attrs
        return story_sublist_attrs(self, kind)

    def _simple_story(self, kind: str, page_type: str, text: str) -> ElementModel:
        from ._hwpx_section import simple_story
        return simple_story(self, kind, page_type, text)

    def _ensure_story(self, kind: str, page_type: str = "BOTH") -> ElementModel:
        page_type = str(page_type).upper()
        if page_type not in {"BOTH", "ODD", "EVEN"}:
            raise ValueError("page_type must be BOTH, ODD, or EVEN")
        existing = self._logical_story(kind, page_type)
        if existing is not None:
            return existing
        story = self._simple_story(kind, page_type, "")
        sec_pr = self._sec_pr()
        sec_pr.children.append(story)
        sec_pr.children.append(ElementModel(HP + kind + "Apply", attrs=[
            ("applyPageType", page_type), ("idRef", story.get("id") or "0")
        ]))
        ctrl = ElementModel(HP + "ctrl")
        ctrl.children.append(ElementModel.from_dict(story.to_dict()))
        run = self._first_run()
        # BOTH goes before page-specific stories so ODD/EVEN can override it.
        insert_at = len(run.children)
        if page_type == "BOTH":
            for i, child in enumerate(run.children):
                if local_name(child.tag) == "ctrl" and any(
                    local_name(x.tag) == kind and (x.get("applyPageType", "BOTH") or "BOTH") != "BOTH"
                    for x in child.children
                ):
                    insert_at = i; break
        run.children.insert(insert_at, ctrl)
        return story

    def _set_story_text(self, kind: str, page_type: str, text: str) -> HeaderFooter:
        story = self._ensure_story(kind, page_type)
        replacement = self._simple_story(kind, page_type, text)
        replacement.set("id", story.get("id") or replacement.get("id") or "0")
        story.children = replacement.children
        self._sync_story(kind, page_type, story)
        return HeaderFooter(story, self, kind)

    def _sync_story(self, kind: str, page_type: str, story: ElementModel) -> None:
        mirror = self._control_story(kind, page_type, story.get("id"))
        if mirror is None:
            ctrl = ElementModel(HP + "ctrl")
            mirror = ElementModel.from_dict(story.to_dict())
            ctrl.children.append(mirror)
            self._first_run().children.append(ctrl)
        else:
            mirror.attrs = list(story.attrs)
            mirror.children = [ElementModel.from_dict(c.to_dict()) for c in story.children]
            mirror.text = story.text
            mirror.tail = story.tail

    def sync_story_mirrors(self) -> None:
        sec_pr = self._sec_pr()
        for story in list(sec_pr.children):
            kind = local_name(story.tag)
            if kind not in {"header", "footer"}:
                continue
            self._sync_story(kind, story.get("applyPageType", "BOTH") or "BOTH", story)

    def get_header(self, page_type: str = "BOTH") -> HeaderFooter | None:
        page_type = str(page_type).upper()
        story = self._logical_story("header", page_type) or self._control_story("header", page_type)
        return None if story is None else HeaderFooter(story, self, "header")

    def get_footer(self, page_type: str = "BOTH") -> HeaderFooter | None:
        page_type = str(page_type).upper()
        story = self._logical_story("footer", page_type) or self._control_story("footer", page_type)
        return None if story is None else HeaderFooter(story, self, "footer")

    def set_header_text(self, text: str, page_type: str = "BOTH") -> HeaderFooter:
        return self._set_story_text("header", str(page_type).upper(), text)

    def set_footer_text(self, text: str, page_type: str = "BOTH") -> HeaderFooter:
        return self._set_story_text("footer", str(page_type).upper(), text)

    @property
    def header(self) -> HeaderFooter:
        return self.get_header("BOTH") or HeaderFooter(self._ensure_story("header", "BOTH"), self, "header")

    @property
    def footer(self) -> HeaderFooter:
        return self.get_footer("BOTH") or HeaderFooter(self._ensure_story("footer", "BOTH"), self, "footer")

    @property
    def even_page_header(self) -> HeaderFooter:
        return self.get_header("EVEN") or HeaderFooter(self._ensure_story("header", "EVEN"), self, "header")

    @property
    def even_page_footer(self) -> HeaderFooter:
        return self.get_footer("EVEN") or HeaderFooter(self._ensure_story("footer", "EVEN"), self, "footer")

    @property
    def odd_page_header(self) -> HeaderFooter:
        return self.get_header("ODD") or HeaderFooter(self._ensure_story("header", "ODD"), self, "header")

    @property
    def odd_page_footer(self) -> HeaderFooter:
        return self.get_footer("ODD") or HeaderFooter(self._ensure_story("footer", "ODD"), self, "footer")

    @property
    def orientation(self):
        from .enum.section import WD_ORIENTATION
        return WD_ORIENTATION.PORTRAIT if (self.page_setup.landscape or "WIDELY").upper() == "WIDELY" else WD_ORIENTATION.LANDSCAPE

    @orientation.setter
    def orientation(self, value) -> None:
        from .enum.section import WD_ORIENTATION
        if isinstance(value, WD_ORIENTATION):
            normalized = value
        else:
            raw = str(getattr(value, "name", value)).strip().upper()
            aliases = {"PORTRAIT": WD_ORIENTATION.PORTRAIT, "LANDSCAPE": WD_ORIENTATION.LANDSCAPE, "WIDELY": WD_ORIENTATION.PORTRAIT, "NARROWLY": WD_ORIENTATION.LANDSCAPE}
            if raw not in aliases:
                raise HwpxValueError("orientation must be PORTRAIT or LANDSCAPE", code="section-orientation-invalid", context={"requested": raw})
            normalized = aliases[raw]
        self.page_setup.landscape = "WIDELY" if normalized == WD_ORIENTATION.PORTRAIT else "NARROWLY"

    page_width = property(lambda self: self.page_setup.width, lambda self, v: setattr(self.page_setup, "width", v))
    page_height = property(lambda self: self.page_setup.height, lambda self, v: setattr(self.page_setup, "height", v))
    left_margin = property(lambda self: self.page_setup.left_margin, lambda self, v: setattr(self.page_setup, "left_margin", v))
    right_margin = property(lambda self: self.page_setup.right_margin, lambda self, v: setattr(self.page_setup, "right_margin", v))
    top_margin = property(lambda self: self.page_setup.top_margin, lambda self, v: setattr(self.page_setup, "top_margin", v))
    bottom_margin = property(lambda self: self.page_setup.bottom_margin, lambda self, v: setattr(self.page_setup, "bottom_margin", v))
    header_distance = property(lambda self: self.page_setup.header_distance, lambda self, v: setattr(self.page_setup, "header_distance", v))
    footer_distance = property(lambda self: self.page_setup.footer_distance, lambda self, v: setattr(self.page_setup, "footer_distance", v))
    gutter = property(lambda self: self.page_setup.gutter, lambda self, v: setattr(self.page_setup, "gutter", v))

    @property
    def first_page_header(self):
        raise HwpxUnsupportedError(
            "HWPX has no verified distinct first-page header story equivalent to DOCX titlePg; "
            "use header/even_page_header/odd_page_header or a dedicated first-page section.",
            code="first-page-header-unverified",
        )

    @property
    def first_page_footer(self):
        raise HwpxUnsupportedError(
            "HWPX has no verified distinct first-page footer story equivalent to DOCX titlePg; "
            "use footer/even_page_footer/odd_page_footer or a dedicated first-page section.",
            code="first-page-footer-unverified",
        )


class Run(NodeProxy):
    @property
    def char_pr_id_ref(self) -> str | None:
        return self._model.get("charPrIDRef")

    @char_pr_id_ref.setter
    def char_pr_id_ref(self, value: str | int) -> None:
        self._model.set("charPrIDRef", str(value))

    @property
    def text(self) -> str:
        return "".join(_text_element_string(node) for node in self._model.children if local_name(node.tag) == "t")

    @text.setter
    def text(self, value: str | None) -> None:
        # Keep controls/objects in place but replace visible text atoms with one
        # native mixed-content hp:t. This mirrors python-docx's text semantics.
        first_index = next((i for i, node in enumerate(self._model.children) if local_name(node.tag) == "t"), len(self._model.children))
        self._model.children[:] = [node for node in self._model.children if local_name(node.tag) != "t"]
        self._model.children.insert(min(first_index, len(self._model.children)), _mixed_text_element(value))
        paragraph = self._parent_paragraph()
        if paragraph is not None:
            paragraph._clear_layout_cache()

    @property
    def font(self):
        from .styles import Font
        return Font(self)

    @property
    def style(self):
        """Best matching named character style, or ``None`` when inherited/ambiguous.

        HWPX stores a ``charPrIDRef`` rather than a direct named-style
        reference. A run whose character properties match its paragraph
        style is treated as having no direct character style, matching
        python-docx's ``Run.style is None`` inheritance semantics.
        """
        if self.document is None:
            return None
        paragraph = self._parent_paragraph()
        if paragraph is not None and paragraph.style is not None:
            inherited_ref = paragraph.style.char_pr_id_ref or "0"
            if (self.char_pr_id_ref or "0") == inherited_ref:
                return None
        matches = [
            style for style in self.document.styles
            if style.style_type is not None
            and style.style_type.name == "CHARACTER"
            and (style.char_pr_id_ref or "0") == (self.char_pr_id_ref or "0")
        ]
        return matches[0] if len(matches) == 1 else None

    @style.setter
    def style(self, value) -> None:
        if self.document is None:
            raise RuntimeError("run is not attached to a document")
        if value is None:
            paragraph = self._parent_paragraph()
            inherited = None if paragraph is None or paragraph.style is None else paragraph.style.char_pr_id_ref
            self.char_pr_id_ref = inherited or "0"
            return
        style = self.document.styles.resolve(value)
        from .enum.style import WD_STYLE_TYPE
        if style.style_type != WD_STYLE_TYPE.CHARACTER:
            raise ValueError("run style must be a character style")
        self.char_pr_id_ref = style.char_pr_id_ref or "0"

    @property
    def bold(self) -> bool:
        return self.font.bold

    @bold.setter
    def bold(self, value: bool) -> None:
        self.font.bold = value

    @property
    def italic(self) -> bool:
        return self.font.italic

    @italic.setter
    def italic(self, value: bool) -> None:
        self.font.italic = value

    @property
    def underline(self) -> bool:
        return self.font.underline

    @underline.setter
    def underline(self, value: bool) -> None:
        self.font.underline = value

    def clear(self) -> "Run":
        """Remove run content while retaining character style and section setup.

        The first HWPX run can carry ``secPr``/section-start controls. Those
        structural nodes are preserved so a python-docx-like ``clear()`` can
        never accidentally corrupt the document section.
        """
        structural_controls = {"colPr", "header", "footer", "pageNum", "pageNumCtrl", "pageHiding", "newNum"}
        kept: list[ElementModel] = []
        for child in self._model.children:
            lname = local_name(child.tag)
            if lname == "secPr":
                kept.append(child)
            elif lname == "ctrl" and any(local_name(x.tag) in structural_controls for x in child.children):
                kept.append(child)
        self._model.children = kept
        self._model.children.append(_mixed_text_element(""))
        paragraph = self._parent_paragraph()
        if paragraph is not None:
            paragraph._clear_layout_cache()
        return self

    def add_tab(self) -> "Run":
        """Append a Hancom-compatible tab inside the run's ``hp:t`` node.

        Real Hancom output stores tabs as mixed content
        ``<hp:t>before<hp:tab/>after</hp:t>``.  A run-level sibling
        ``<hp:tab/>`` is not the native representation and can be discarded
        by Hancom.
        """
        t = next((c for c in reversed(self._model.children) if local_name(c.tag) == "t"), None)
        if t is None:
            t = ElementModel(HP + "t", text="")
            self._model.children.append(t)
        t.children.append(ElementModel(HP + "tab"))
        paragraph = self._parent_paragraph()
        if paragraph is not None:
            paragraph._clear_layout_cache()
        return self

    def _parent_paragraph(self) -> "Paragraph | None":
        # Paragraph-created runs retain their native parent for O(1) layout
        # invalidation. A full document walk per edited run made batch HWPX
        # text replacement quadratic in document paragraph count.
        parent = getattr(self, "_known_parent_paragraph", None)
        if parent is not None and any(child is self._model for child in parent.element_model.children):
            return parent
        if self.document is None:
            return None
        for paragraph in self.document.all_paragraphs:
            if any(child is self._model for child in paragraph.element_model.children):
                return paragraph
        return None

    def add_break(self, break_type: str = "LINE") -> "Run":
        """Add LINE/PAGE/COLUMN break using HWPX-native representation."""
        raw = getattr(break_type, "value", break_type)
        kind = str(raw).strip().upper()
        aliases = {"LINE":"LINE", "TEXT_WRAPPING":"LINE", "PAGE":"PAGE", "COLUMN":"COLUMN"}
        if kind not in aliases:
            raise HwpxValueError("break_type must be LINE, PAGE, or COLUMN", code="run-break-type-invalid", context={"requested": str(raw)})
        kind = aliases[kind]
        if kind == "LINE":
            # Real Hancom output nests lineBreak inside hp:t, unlike hp:tab.
            t = next((c for c in reversed(self._model.children) if local_name(c.tag) == "t"), None)
            if t is None:
                t = ElementModel(HP + "t", text="")
                self._model.children.append(t)
            t.children.append(ElementModel(HP + "lineBreak"))
            paragraph = self._parent_paragraph()
            if paragraph is not None:
                paragraph._clear_layout_cache()
        else:
            paragraph = self._parent_paragraph()
            if paragraph is None:
                raise RuntimeError("run is not attached to a paragraph")
            paragraph.element_model.set("pageBreak" if kind == "PAGE" else "columnBreak", "1")
        return self


class Hyperlink(NodeProxy):
    """A HWPX hyperlink field plus its visible run."""

    def __init__(self, field_begin: ElementModel, display_run: ElementModel, paragraph: "Paragraph"):
        super().__init__(field_begin, paragraph.document)
        self._display_run = display_run
        self.paragraph = paragraph

    @property
    def id(self) -> str:
        return self._model.get("id", "") or ""

    @property
    def url(self) -> str:
        return _hyperlink_target(self._model)

    @property
    def text(self) -> str:
        return "".join(_text_element_string(n) for n in self._display_run.children if local_name(n.tag) == "t")

    @text.setter
    def text(self, value: str) -> None:
        first = next((i for i, n in enumerate(self._display_run.children) if local_name(n.tag) == "t"), len(self._display_run.children))
        self._display_run.children[:] = [n for n in self._display_run.children if local_name(n.tag) != "t"]
        self._display_run.children.insert(min(first, len(self._display_run.children)), _mixed_text_element(value))
        self.paragraph._clear_layout_cache()


class Paragraph(NodeProxy):
    @property
    def para_pr_id_ref(self) -> str | None:
        return self._model.get("paraPrIDRef")

    @para_pr_id_ref.setter
    def para_pr_id_ref(self, value: str | int) -> None:
        self._model.set("paraPrIDRef", str(value))

    @property
    def style_id_ref(self) -> str | None:
        return self._model.get("styleIDRef")

    @style_id_ref.setter
    def style_id_ref(self, value: str | int) -> None:
        self._model.set("styleIDRef", str(value))

    @property
    def style(self):
        if self.document is None:
            return None
        return self.document.styles.get(self.style_id_ref)

    @style.setter
    def style(self, value) -> None:
        if self.document is None:
            raise RuntimeError("paragraph is not attached to a document")
        old_style = self.style
        old_inherited_char_ref = None if old_style is None else (old_style.char_pr_id_ref or "0")
        style = self.document.styles.default("PARAGRAPH") if value is None else self.document.styles.resolve(value)
        if style is None:
            raise RuntimeError("document has no default paragraph style")
        from .enum.style import WD_STYLE_TYPE
        if style.style_type != WD_STYLE_TYPE.PARAGRAPH:
            raise ValueError("paragraph style must be a paragraph style")
        self.style_id_ref = style.id
        if style.para_pr_id_ref is not None:
            self.para_pr_id_ref = style.para_pr_id_ref
        # HWPX stores flat charPr records rather than DOCX-style inheritance.
        # Rebase visible run formatting so direct overrides survive while
        # unrelated properties can still inherit from the newly assigned
        # paragraph style. Structural control-only runs are left untouched.
        if style.char_pr_id_ref is not None and old_inherited_char_ref is not None:
            for run in self.runs:
                if not any(local_name(child.tag) == "t" for child in run.element_model.children):
                    continue
                run.char_pr_id_ref = self.document.styles.rebase_char_property(
                    run.char_pr_id_ref, old_inherited_char_ref, style.char_pr_id_ref
                )

    def _wrap_run(self, model: ElementModel) -> Run:
        run = Run(model, self.document)
        run._known_parent_paragraph = self
        return run

    @property
    def runs(self) -> list[Run]:
        return [self._wrap_run(c) for c in self._model.children if local_name(c.tag) == "run"]

    def _clear_layout_cache(self) -> None:
        """Drop direct line-layout cache after visible paragraph content changes."""
        self._model.children[:] = [
            child for child in self._model.children if local_name(child.tag) != "linesegarray"
        ]

    def replace(self, search: str, replacement: str, count: int = -1) -> int:
        """Replace visible text across run/hyperlink boundaries without rebuilding the paragraph.

        Replacement text inherits the formatting/container of the first matched
        visible segment. Existing runs and hyperlink field controls are retained.
        This is the structure-preserving counterpart to assigning ``paragraph.text``.
        """
        if not search:
            raise HwpxValueError("search must not be empty", code="text-search-empty")
        if count == 0:
            return 0
        objects = list(self.iter_inner_content())
        texts = [obj.text for obj in objects]
        combined = "".join(texts)
        matches: list[tuple[int, int]] = []
        cursor = 0
        limit = None if count is None or int(count) < 0 else int(count)
        while True:
            if limit is not None and len(matches) >= limit:
                break
            start = combined.find(search, cursor)
            if start < 0:
                break
            end = start + len(search)
            matches.append((start, end))
            cursor = end
        if not matches:
            return 0

        starts: list[int] = []
        pos = 0
        for text in texts:
            starts.append(pos)
            pos += len(text)

        def locate(char_index: int) -> tuple[int, int]:
            for i, (base, text) in enumerate(zip(starts, texts)):
                if base <= char_index < base + len(text):
                    return i, char_index - base
            raise IndexError(char_index)

        for start, end in reversed(matches):
            first_i, first_off = locate(start)
            last_i, last_off = locate(end - 1)
            end_off = last_off + 1
            if first_i == last_i:
                text = objects[first_i].text
                objects[first_i].text = text[:first_off] + replacement + text[end_off:]
            else:
                first_text = objects[first_i].text
                last_text = objects[last_i].text
                objects[first_i].text = first_text[:first_off] + replacement
                for i in range(first_i + 1, last_i):
                    objects[i].text = ""
                objects[last_i].text = last_text[end_off:]
        self._clear_layout_cache()
        return len(matches)

    @property
    def text(self) -> str:
        # Only direct runs belong to this paragraph's visible text. Descending
        # through inline tables/notes would leak nested story text into the host
        # paragraph, unlike python-docx semantics.
        return "".join(run.text for run in self.runs)

    @text.setter
    def text(self, value: str | None) -> None:
        self.clear()
        runs = self.runs
        if runs:
            last = runs[-1]
            # clear() leaves one empty text run so an empty HWPX paragraph
            # remains structurally safe. Reuse it rather than creating a
            # second run, matching python-docx's single-run replacement.
            if all(local_name(c.tag) == "t" for c in last.element_model.children):
                last.text = value
                return
        self.add_run(value)

    @property
    def paragraph_format(self):
        from .styles import ParagraphFormat
        return ParagraphFormat(self)

    @property
    def alignment(self) -> str | None:
        return self.paragraph_format.alignment

    @alignment.setter
    def alignment(self, value: str) -> None:
        self.paragraph_format.alignment = value

    @property
    def page_break(self) -> bool:
        return self._model.get("pageBreak", "0") == "1"

    @page_break.setter
    def page_break(self, value: bool) -> None:
        self._model.set("pageBreak", "1" if value else "0")

    @property
    def column_break(self) -> bool:
        return self._model.get("columnBreak", "0") == "1"

    @column_break.setter
    def column_break(self, value: bool) -> None:
        self._model.set("columnBreak", "1" if value else "0")

    @property
    def contains_page_break(self) -> bool:
        """Whether this paragraph carries an explicit HWPX page break."""
        return self.page_break

    def clear(self) -> "Paragraph":
        """Remove paragraph content while preserving paragraph-level formatting.

        HWPX stores section-start controls inside the first paragraph. Those are
        structural rather than user content and must survive ``clear()``.
        """
        structural_controls = {"colPr", "header", "footer", "pageNum", "pageNumCtrl", "pageHiding", "newNum"}
        kept_runs: list[ElementModel] = []
        for child in self._model.children:
            if local_name(child.tag) != "run":
                continue
            kept_children: list[ElementModel] = []
            for node in child.children:
                lname = local_name(node.tag)
                if lname == "secPr":
                    kept_children.append(node)
                    continue
                if lname == "ctrl" and any(local_name(x.tag) in structural_controls for x in node.children):
                    kept_children.append(node)
            if kept_children:
                clone = ElementModel(HP + "run", attrs=list(child.attrs), children=kept_children)
                kept_runs.append(clone)
        self._model.children = kept_runs
        self.add_run("")
        return self

    def add_run(self, text: str | None = None, style=None, *, char_pr_id_ref: str | int | None = None) -> Run:
        if self.document is not None and style is not None:
            style_obj = self.document.styles.resolve(style)
            if (style_obj.type or "").upper() not in {"CHAR", "CHARACTER"}:
                raise ValueError("run style must be a character style")
            char_pr_id_ref = style_obj.char_pr_id_ref or "0"
        if char_pr_id_ref is None:
            # Prefer the last visible-content run. Section setup can live in a
            # structural run with charPrIDRef=0 and must not accidentally reset
            # the character properties inherited from a paragraph style.
            content_runs = [
                run for run in self.runs
                if any(local_name(child.tag) == "t" for child in run.element_model.children)
            ]
            if content_runs:
                char_pr_id_ref = content_runs[-1].char_pr_id_ref or "0"
            elif self.style is not None:
                char_pr_id_ref = self.style.char_pr_id_ref or "0"
            else:
                char_pr_id_ref = "0"
        run_model = ElementModel(HP + "run", attrs=[("charPrIDRef", str(char_pr_id_ref))])
        run_model.children.append(_mixed_text_element(text))
        # Runs belong before layout caches such as linesegarray.
        insert_at = len(self._model.children)
        for i, child in enumerate(self._model.children):
            if local_name(child.tag) == "linesegarray":
                insert_at = i
                break
        self._model.children.insert(insert_at, run_model)
        self._clear_layout_cache()
        return self._wrap_run(run_model)

    def _insert_runs_before_layout_cache(self, runs: list[ElementModel]) -> None:
        insert_at = len(self._model.children)
        for i, child in enumerate(self._model.children):
            if local_name(child.tag) == "linesegarray":
                insert_at = i
                break
        self._model.children[insert_at:insert_at] = runs

    def insert_paragraph_before(self, text: str | None = None, style=None) -> "Paragraph":
        """Insert and return a paragraph immediately before this one."""
        if self.document is None:
            raise RuntimeError("paragraph is not attached to a document")
        parent = None
        for section in self.document.section_models:
            for candidate in section.iter():
                if any(child is self._model for child in candidate.children):
                    parent = candidate
                    break
            if parent is not None:
                break
        if parent is None:
            raise RuntimeError("paragraph parent could not be located")
        from .authoring import paragraph_attrs
        model = ElementModel(HP + "p", attrs=paragraph_attrs())
        paragraph = Paragraph(model, self.document)
        if text is not None:
            paragraph.add_run(text)
        if style is not None:
            paragraph.style = style
        index = next(i for i, child in enumerate(parent.children) if child is self._model)
        parent.children.insert(index, model)

        # Hancom expects secPr and section-start controls in the first
        # paragraph of a section. Inserting before that carrier without moving
        # them can make Hancom interpret the old carrier as a second section.
        if local_name(parent.tag) == "sec" and index == 0:
            structural_controls = {
                "colPr", "header", "footer", "pageNum", "pageNumCtrl",
                "pageHiding", "newNum",
            }
            moved: list[ElementModel] = []
            for run in [c for c in self._model.children if local_name(c.tag) == "run"]:
                keep: list[ElementModel] = []
                for child in run.children:
                    lname = local_name(child.tag)
                    if lname == "secPr":
                        moved.append(child)
                    elif lname == "ctrl" and any(
                        local_name(x.tag) in structural_controls for x in child.children
                    ):
                        moved.append(child)
                    else:
                        keep.append(child)
                run.children = keep
            if moved:
                control_run = ElementModel(HP + "run", attrs=[("charPrIDRef", "0")], children=moved)
                model.children.insert(0, control_run)
        return paragraph

    def iter_inner_content(self):
        """Yield runs and hyperlinks in paragraph order, python-docx style."""
        hyperlink_by_begin = {h.id: h for h in self.hyperlinks}
        skipping: str | None = None
        for child in self._model.children:
            if local_name(child.tag) != "run":
                continue
            begin = next((n for n in child.iter() if local_name(n.tag) == "fieldBegin" and n.get("type") == "HYPERLINK"), None)
            if begin is not None:
                skipping = begin.get("id") or ""
                link = hyperlink_by_begin.get(skipping)
                if link is not None:
                    yield link
                continue
            if skipping is not None:
                end = next((n for n in child.iter() if local_name(n.tag) == "fieldEnd" and n.get("beginIDRef") == skipping), None)
                if end is not None:
                    skipping = None
                continue
            yield self._wrap_run(child)

    @property
    def bookmarks(self) -> list[str]:
        names: list[str] = []
        for run in self.runs:
            for node in run.element_model.iter():
                if local_name(node.tag) == "bookmark" and node.get("name"):
                    names.append(node.get("name") or "")
        return names

    def add_bookmark(self, name: str, *, char_pr_id_ref: str | int | None = None) -> ElementModel:
        value = str(name).strip()
        if not value:
            raise ValueError("bookmark name must not be empty")
        if char_pr_id_ref is None:
            existing = self.runs
            char_pr_id_ref = existing[-1].char_pr_id_ref if existing else "0"
        run = ElementModel(HP + "run", attrs=[("charPrIDRef", str(char_pr_id_ref or "0"))])
        ctrl = ElementModel(HP + "ctrl")
        bookmark = ElementModel(HP + "bookmark", attrs=[("name", value)])
        ctrl.children.append(bookmark)
        run.children.append(ctrl)
        self._insert_runs_before_layout_cache([run])
        return bookmark

    @property
    def hyperlinks(self) -> list[Hyperlink]:
        runs = [c for c in self._model.children if local_name(c.tag) == "run"]
        result: list[Hyperlink] = []
        for i, run in enumerate(runs):
            begin = next((n for n in run.iter() if local_name(n.tag) == "fieldBegin" and n.get("type") == "HYPERLINK"), None)
            if begin is None:
                continue
            begin_id = begin.get("id") or ""
            display = None
            for following in runs[i + 1:]:
                end = next((n for n in following.iter() if local_name(n.tag) == "fieldEnd" and n.get("beginIDRef") == begin_id), None)
                if end is not None:
                    break
                if display is None and any(local_name(n.tag) == "t" for n in following.children):
                    display = following
            if display is not None:
                result.append(Hyperlink(begin, display, self))
        return result

    def add_hyperlink(
        self, url: str, display_text: str, *, char_pr_id_ref: str | int | None = None
    ) -> Hyperlink:
        target = str(url).strip()
        if not target:
            raise ValueError("hyperlink target must not be empty")
        from .authoring import object_id
        existing = self.runs
        ambient = existing[-1].char_pr_id_ref if existing else "0"
        ambient = ambient or "0"
        if char_pr_id_ref is None:
            if self.document is not None:
                char_pr_id_ref = self.document.styles.ensure_run(
                    base_char_pr_id=ambient, underline=True, underline_color="#0000FF", color="#0000FF"
                )
            else:
                char_pr_id_ref = ambient
        field_id = object_id()

        begin_run = ElementModel(HP + "run", attrs=[("charPrIDRef", str(ambient))])
        begin_ctrl = ElementModel(HP + "ctrl")
        begin = ElementModel(HP + "fieldBegin", attrs=[
            ("id", field_id), ("type", "HYPERLINK"), ("name", target),
            ("editable", "0"), ("dirty", "0"), ("zorder", "-1"),
            ("fieldid", _HYPERLINK_FIELD_ID),
        ])
        params = _hyperlink_parameters(target)
        holder = ElementModel(HP + "parameters", attrs=[("cnt", str(len(params))), ("name", "")])
        for kind, name, text in params:
            holder.children.append(ElementModel(HP + kind, attrs=[("name", name)], text=text))
        begin.children.append(holder)
        begin_ctrl.children.append(begin)
        begin_run.children.append(begin_ctrl)

        display_run = ElementModel(HP + "run", attrs=[("charPrIDRef", str(char_pr_id_ref))])
        display_run.children.append(ElementModel(HP + "t", text=str(display_text)))

        end_run = ElementModel(HP + "run", attrs=[("charPrIDRef", str(ambient))])
        end_ctrl = ElementModel(HP + "ctrl")
        end_ctrl.children.append(ElementModel(HP + "fieldEnd", attrs=[
            ("beginIDRef", field_id), ("fieldid", _HYPERLINK_FIELD_ID),
        ]))
        end_run.children.append(end_ctrl)
        self._insert_runs_before_layout_cache([begin_run, display_run, end_run])
        return Hyperlink(begin, display_run, self)

    def _append_inline_object(self, obj: ElementModel, *, char_pr_id_ref: str | int = "0") -> Run:
        run_model = ElementModel(HP + "run", attrs=[("charPrIDRef", str(char_pr_id_ref))])
        run_model.children.append(obj)
        insert_at = len(self._model.children)
        for i, child in enumerate(self._model.children):
            if local_name(child.tag) == "linesegarray":
                insert_at = i
                break
        self._model.children.insert(insert_at, run_model)
        return self._wrap_run(run_model)

    def add_table(
        self, rows: int, cols: int, *, width: int | None = None, height: int | None = None,
        border_fill_id_ref: str | int | None = None,
    ) -> "Table":
        from .authoring import create_table
        if self.document is None:
            raise RuntimeError("paragraph is not attached to a document")
        if border_fill_id_ref is None:
            border_fill_id_ref = self.document.styles.ensure_border_fill(
                base_border_fill_id="1", color="#000000", width="0.12 mm", border_type="SOLID"
            )
        model = create_table(rows, cols, width=width, height=height, border_fill_id_ref=border_fill_id_ref)
        self._append_inline_object(model)
        return Table(model, self.document)

    def add_rectangle(
        self, width: int = 14400, height: int = 7200, *, text: str | None = None,
        line_color: str = "#000000", line_width: str = "33", fill_color: str | None = None,
        treat_as_char: bool = True, char_pr_id_ref: str | int = "0", para_pr_id_ref: str | int = "0",
    ) -> "Rectangle":
        from .authoring import create_rectangle
        model = create_rectangle(
            width, height, text=text, line_color=line_color, line_width=line_width,
            fill_color=fill_color, treat_as_char=treat_as_char,
            char_pr_id_ref=char_pr_id_ref, para_pr_id_ref=para_pr_id_ref,
        )
        self._append_inline_object(model, char_pr_id_ref=char_pr_id_ref)
        return Rectangle(model, self.document)

    def add_picture(
        self, binary_item_id_ref: str, *, width: int = 14400, height: int = 14400,
        treat_as_char: bool = True, char_pr_id_ref: str | int = "0",
    ) -> "Picture":
        from .authoring import create_picture
        model = create_picture(binary_item_id_ref, width, height, treat_as_char=treat_as_char)
        self._append_inline_object(model, char_pr_id_ref=char_pr_id_ref)
        return Picture(model, self.document)

    def add_equation(
        self, script: str, *, base_unit: int = 1100, size: tuple[int, int] | None = None,
        char_pr_id_ref: str | int | None = None,
    ) -> ElementModel:
        """Insert an inline EqEdit equation (``hp:equation/hp:script``)."""
        text = str(script).strip()
        if not text:
            raise ValueError("equation script must not be empty")
        if base_unit <= 0:
            raise ValueError("base_unit must be positive")
        from .authoring import object_id
        if size is None:
            width = max(2200, int(base_unit * (0.7 * len(text) + 1.5)))
            height = max(1800, int(base_unit * 1.8))
        else:
            width, height = map(int, size)
        eq = ElementModel(HP + "equation", attrs=[
            ("id", object_id()), ("zOrder","0"), ("numberingType","EQUATION"),
            ("textWrap","TOP_AND_BOTTOM"), ("textFlow","BOTH_SIDES"), ("lock","0"),
            ("dropcapstyle","None"), ("version","Equation Version 60"),
            ("baseLine", str(base_unit)), ("textColor","#000000"),
            ("baseUnit",str(base_unit)), ("lineMode","CHAR"), ("font","HYhwpEQ"),
        ])
        eq.children.extend([
            ElementModel(HP+"sz", attrs=[("width",str(width)),("widthRelTo","ABSOLUTE"),("height",str(height)),("heightRelTo","ABSOLUTE"),("protect","0")]),
            ElementModel(HP+"pos", attrs=[("treatAsChar","1"),("affectLSpacing","0"),("flowWithText","1"),("allowOverlap","0"),("holdAnchorAndSO","0"),("vertRelTo","PARA"),("horzRelTo","PARA"),("vertAlign","TOP"),("horzAlign","LEFT"),("vertOffset","0"),("horzOffset","0")]),
            ElementModel(HP+"outMargin", attrs=[("left","56"),("right","56"),("top","0"),("bottom","0")]),
            ElementModel(HP+"shapeComment", text="수식입니다."),
            ElementModel(HP+"script", text=text),
        ])
        self._append_inline_object(eq, char_pr_id_ref=char_pr_id_ref or "0")
        return eq

    def add_memo(
        self, text: str, *, author: str = "", memo_shape_id_ref: str | int = "65535"
    ) -> ElementModel:
        """Attach a visible MEMO field and section-level memo body to this paragraph."""
        if self.document is None:
            raise RuntimeError("paragraph is not attached to a document")
        from .authoring import object_id, paragraph_attrs, sublist_attrs
        section = self.document.section_for_descendant(self.element_model)
        if section is None:
            raise RuntimeError("paragraph has no owning section")
        memo_id = object_id(); field_id = object_id()
        group = next((c for c in section.element_model.children if local_name(c.tag)=="memogroup"), None)
        if group is None:
            group = ElementModel(HP+"memogroup"); section.element_model.children.append(group)
        memo = ElementModel(HP+"memo", attrs=[("id",memo_id),("memoShapeIDRef",str(memo_shape_id_ref))])
        plist = ElementModel(HP+"paraList")
        mp = ElementModel(HP+"p", attrs=paragraph_attrs(style_id_ref="17", para_pr_id_ref="11")); mp.set("id","0")
        mr = ElementModel(HP+"run", attrs=[("charPrIDRef","4")]); mr.children.append(ElementModel(HP+"t", text=str(text)))
        mp.children.append(mr); plist.children.append(mp); memo.children.append(plist); group.children.append(memo)
        ambient = self.runs[-1].char_pr_id_ref if self.runs else "0"
        begin_run=ElementModel(HP+"run", attrs=[("charPrIDRef",str(ambient or "0"))]); bc=ElementModel(HP+"ctrl")
        fb=ElementModel(HP+"fieldBegin", attrs=[("id",field_id),("type","MEMO"),("name",""),("editable","1"),("dirty","0"),("zorder","1"),("fieldid",str(int.from_bytes(b"%%me","big")))])
        params=ElementModel(HP+"parameters", attrs=[("cnt","5"),("name","")])
        for kind,name,val in [("stringParam","ID",memo_id),("integerParam","Number","1"),("stringParam","CreateDateTime",""),("stringParam","Author",author),("stringParam","MemoShapeIDRef",str(memo_shape_id_ref))]:
            params.children.append(ElementModel(HP+kind, attrs=[("name",name)], text=str(val)))
        fb.children.append(params)
        sub=ElementModel(HP+"subList", attrs=sublist_attrs()); sp=ElementModel(HP+"p", attrs=paragraph_attrs()); sp.set("id","0")
        sr=ElementModel(HP+"run", attrs=[("charPrIDRef",str(ambient or "0"))]); sr.children.append(ElementModel(HP+"t", text=str(text))); sp.children.append(sr); sub.children.append(sp); fb.children.append(sub); bc.children.append(fb); begin_run.children.append(bc)
        end_run=ElementModel(HP+"run", attrs=[("charPrIDRef",str(ambient or "0"))]); ec=ElementModel(HP+"ctrl"); ec.children.append(ElementModel(HP+"fieldEnd", attrs=[("beginIDRef",field_id),("fieldid",str(int.from_bytes(b"%%me","big")))])); end_run.children.append(ec)
        self._insert_runs_before_layout_cache([begin_run,end_run])
        return memo

    def set_list(
        self, *, kind: str = "bullet", level: int = 0,
        levels: list[dict[str, str]] | None = None, restart: bool = False,
        start: int | None = None,
    ) -> "Paragraph":
        if self.document is None:
            raise RuntimeError("paragraph is not attached to a document")
        if level < 0:
            raise ValueError("level must be non-negative")
        specs = [dict(item) for item in (levels or [{} for _ in range(level + 1)])]
        while len(specs) <= level:
            specs.append({})
        if start is not None:
            if int(start) < 1:
                raise ValueError("list start must be >= 1")
            specs[level]["start"] = str(int(start))
        refs = self.document.styles.ensure_numbering(kind=kind, levels=specs, restart=restart)
        if level >= len(refs):
            raise ValueError("level is out of range for numbering definition")
        self.para_pr_id_ref = refs[level]
        return self

    def _note_style_refs(self, kind: str) -> tuple[str, str, str]:
        if self.document is None:
            fallback = {"footNote": ("15", "10", "3"), "endNote": ("16", "10", "3")}
            return fallback[kind]
        label = "각주" if kind == "footNote" else "미주"
        style = self.document.styles.get(label)
        if style is None:
            fallback = {"footNote": ("15", "10", "3"), "endNote": ("16", "10", "3")}
            return fallback[kind]
        return (style.id, style.para_pr_id_ref or "10", style.char_pr_id_ref or "3")

    def _note_suffix(self, kind: str) -> str:
        if self.document is None:
            return ")"
        section = self.document.section_for_descendant(self.element_model)
        if section is None:
            return ")"
        sec_pr = section._sec_pr()
        pr = next((c for c in sec_pr.children if local_name(c.tag) == kind + "Pr"), None)
        if pr is not None:
            fmt = next((c for c in pr.children if local_name(c.tag) == "autoNumFormat"), None)
            if fmt is not None and fmt.get("suffixChar"):
                return fmt.get("suffixChar") or ")"
        return ")"

    def _next_note_number(self, kind: str) -> int:
        if self.document is None:
            return 1
        return 1 + sum(
            1
            for section in self.document.section_models
            for node in section.iter()
            if local_name(node.tag) == kind
        )

    def _add_note(
        self, kind: str, text: str, *, char_pr_id_ref: str | int | None = None,
    ) -> "Note":
        from .authoring import object_id, paragraph_attrs, sublist_attrs
        number = self._next_note_number(kind)
        suffix = self._note_suffix(kind)
        style_ref, para_ref, note_char_ref = self._note_style_refs(kind)
        if char_pr_id_ref is not None:
            note_char_ref = str(char_pr_id_ref)

        runs = self.runs
        if runs:
            host = runs[-1].element_model
        else:
            host = self.add_run("", char_pr_id_ref=char_pr_id_ref or "0").element_model
        ctrl = ElementModel(HP + "ctrl")
        note = ElementModel(HP + kind, attrs=[
            ("number", str(number)),
            ("suffixChar", str(ord(suffix[0])) if suffix else "41"),
            ("instId", object_id()),
        ])
        sub_attrs = dict(sublist_attrs()); sub_attrs["vertAlign"] = "TOP"
        sub = ElementModel(HP + "subList", attrs=list(sub_attrs.items()))
        p = ElementModel(HP + "p", attrs=paragraph_attrs(para_pr_id_ref=para_ref, style_id_ref=style_ref))
        # Hancom note paragraphs use id=0 in observed output.
        p.set("id", "0")
        run = ElementModel(HP + "run", attrs=[("charPrIDRef", str(note_char_ref))])
        num_ctrl = ElementModel(HP + "ctrl")
        auto = ElementModel(HP + "autoNum", attrs=[
            ("num", str(number)), ("numType", "FOOTNOTE" if kind == "footNote" else "ENDNOTE")
        ])
        auto.children.append(ElementModel(HP + "autoNumFormat", attrs=[
            ("type", "DIGIT"), ("userChar", ""), ("prefixChar", ""),
            ("suffixChar", suffix), ("supscript", "0"),
        ]))
        num_ctrl.children.append(auto)
        run.children.extend([num_ctrl, ElementModel(HP + "t", text=text)])
        p.children.append(run); sub.children.append(p); note.children.append(sub); ctrl.children.append(note)
        host.children.append(ctrl)
        return Note(note, self.document)

    def add_footnote(self, text: str, *, char_pr_id_ref: str | int | None = None) -> "Note":
        return self._add_note("footNote", text, char_pr_id_ref=char_pr_id_ref)

    def add_endnote(self, text: str, *, char_pr_id_ref: str | int | None = None) -> "Note":
        return self._add_note("endNote", text, char_pr_id_ref=char_pr_id_ref)

    @property
    def footnotes(self) -> list["Note"]:
        return [Note(node, self.document) for node in self._model.iter() if local_name(node.tag) == "footNote"]

    @property
    def endnotes(self) -> list["Note"]:
        return [Note(node, self.document) for node in self._model.iter() if local_name(node.tag) == "endNote"]


class Note(NodeProxy):
    @property
    def number(self) -> int:
        return int(self._model.get("number", "0") or 0)

    @property
    def note_type(self) -> str:
        return local_name(self._model.tag)

    @property
    def paragraphs(self) -> list[Paragraph]:
        sub = next((c for c in self._model.children if local_name(c.tag) == "subList"), None)
        if sub is None:
            return []
        return [Paragraph(p, self.document) for p in sub.children if local_name(p.tag) == "p"]

    @property
    def text(self) -> str:
        return "\n".join(p.text for p in self.paragraphs)

    def add_run(self, text: str, *, bold: bool = False, italic: bool = False, underline: bool = False) -> Run:
        paragraphs = self.paragraphs
        if not paragraphs:
            raise ValueError("note has no paragraph")
        paragraph = paragraphs[-1]
        char_ref = paragraph.runs[-1].char_pr_id_ref if paragraph.runs else "0"
        if self.document is not None and any((bold, italic, underline)):
            char_ref = self.document.styles.ensure_run(
                base_char_pr_id=char_ref,
                bold=bold if bold else None,
                italic=italic if italic else None,
                underline=underline if underline else None,
            )
        return paragraph.add_run(text, char_pr_id_ref=char_ref or "0")


class Cell(NodeProxy):
    @property
    def address(self) -> tuple[int, int]:
        for c in self._model.children:
            if local_name(c.tag) == "cellAddr":
                return int(c.get("rowAddr", "0") or 0), int(c.get("colAddr", "0") or 0)
        return (0, 0)

    @property
    def span(self) -> tuple[int, int]:
        for c in self._model.children:
            if local_name(c.tag) == "cellSpan":
                return int(c.get("rowSpan", "1") or 1), int(c.get("colSpan", "1") or 1)
        return (1, 1)

    def _child(self, name: str) -> ElementModel | None:
        return next((c for c in self._model.children if local_name(c.tag) == name), None)

    def _set_address(self, row: int, col: int) -> None:
        node = self._child("cellAddr")
        if node is None:
            node = ElementModel(HP + "cellAddr")
            self._model.children.append(node)
        node.set("rowAddr", str(int(row)))
        node.set("colAddr", str(int(col)))

    def _set_span(self, row_span: int, col_span: int) -> None:
        node = self._child("cellSpan")
        if node is None:
            node = ElementModel(HP + "cellSpan")
            self._model.children.append(node)
        node.set("rowSpan", str(max(int(row_span), 1)))
        node.set("colSpan", str(max(int(col_span), 1)))

    @property
    def width(self) -> int:
        node = self._child("cellSz")
        return 0 if node is None else int(node.get("width", "0") or 0)

    @width.setter
    def width(self, value: int) -> None:
        node = self._child("cellSz")
        if node is None:
            node = ElementModel(HP + "cellSz", attrs=[("width", "0"), ("height", "0")])
            self._model.children.append(node)
        node.set("width", str(max(int(value), 0)))

    @property
    def height(self) -> int:
        node = self._child("cellSz")
        return 0 if node is None else int(node.get("height", "0") or 0)

    @height.setter
    def height(self, value: int) -> None:
        node = self._child("cellSz")
        if node is None:
            node = ElementModel(HP + "cellSz", attrs=[("width", "0"), ("height", "0")])
            self._model.children.append(node)
        node.set("height", str(max(int(value), 0)))

    @property
    def border_fill_id_ref(self) -> str | None:
        return self._model.get("borderFillIDRef")

    @border_fill_id_ref.setter
    def border_fill_id_ref(self, value: str | int) -> None:
        self._model.set("borderFillIDRef", str(value))

    @property
    def border(self):
        from .styles import CellBorder
        return CellBorder(self)

    @property
    def fill_color(self) -> str | None:
        return self.border.fill_color

    @fill_color.setter
    def fill_color(self, value: str) -> None:
        self.border.fill_color = value

    @property
    def vertical_alignment(self):
        from .enum.table import WD_CELL_VERTICAL_ALIGNMENT
        sub = self._child("subList")
        raw = "CENTER" if sub is None else (sub.get("vertAlign", "CENTER") or "CENTER").upper()
        return {"TOP": WD_CELL_VERTICAL_ALIGNMENT.TOP, "CENTER": WD_CELL_VERTICAL_ALIGNMENT.CENTER, "BOTTOM": WD_CELL_VERTICAL_ALIGNMENT.BOTTOM}.get(raw)

    @vertical_alignment.setter
    def vertical_alignment(self, value) -> None:
        from .authoring import sublist_attrs
        from .enum.table import WD_CELL_VERTICAL_ALIGNMENT
        if isinstance(value, WD_CELL_VERTICAL_ALIGNMENT):
            raw = value.name
        else:
            raw = str(getattr(value, "name", value)).strip().upper()
        if raw not in {"TOP", "CENTER", "BOTTOM"}:
            raise HwpxValueError("cell vertical_alignment must be TOP, CENTER, or BOTTOM", code="cell-vertical-alignment-invalid", context={"requested": raw})
        sub = self._child("subList")
        if sub is None:
            sub = ElementModel(HP + "subList", attrs=sublist_attrs())
            self._model.children.insert(0, sub)
        sub.set("vertAlign", raw)

    @property
    def paragraphs(self) -> list[Paragraph]:
        out: list[Paragraph] = []
        for c in self._model.children:
            if local_name(c.tag) == "subList":
                out.extend(Paragraph(p, self.document) for p in c.children if local_name(p.tag) == "p")
        return out

    @property
    def text(self) -> str:
        return "\n".join(p.text for p in self.paragraphs)

    @text.setter
    def text(self, value: str) -> None:
        """Replace all cell content with one paragraph and one run.

        This matches python-docx semantics more closely than merely blanking
        existing paragraphs: nested tables and other old block content are
        removed from the cell story. The first paragraph/run formatting refs
        are retained when available.
        """
        from .authoring import paragraph_attrs, sublist_attrs
        old_paragraphs = self.paragraphs
        para_ref = old_paragraphs[0].para_pr_id_ref if old_paragraphs else "0"
        style_ref = old_paragraphs[0].style_id_ref if old_paragraphs else "0"
        old_runs = old_paragraphs[0].runs if old_paragraphs else []
        char_ref = (old_runs[0].char_pr_id_ref or "0") if old_runs else "0"
        sub = self._child("subList")
        if sub is None:
            sub = ElementModel(HP + "subList", attrs=sublist_attrs())
            self._model.children.insert(0, sub)
        p = ElementModel(HP + "p", attrs=paragraph_attrs(
            para_pr_id_ref=para_ref or "0", style_id_ref=style_ref or "0"
        ))
        paragraph = Paragraph(p, self.document)
        paragraph.add_run(str(value), char_pr_id_ref=char_ref)
        sub.children = [p]

    @property
    def tables(self) -> list["Table"]:
        """Nested tables directly contained in this cell story."""
        result: list[Table] = []
        sub = self._child("subList")
        if sub is None:
            return result
        for p in sub.children:
            if local_name(p.tag) != "p":
                continue
            for run in p.children:
                if local_name(run.tag) != "run":
                    continue
                for child in run.children:
                    if local_name(child.tag) == "tbl":
                        result.append(Table(child, self.document))
        return result

    def iter_inner_content(self):
        """Yield Paragraph and nested Table blocks in cell order.

        HWPX carries tables inside paragraph/run wrappers. A wrapper that only
        exists to host table objects is hidden here, matching python-docx's
        block-level traversal model.
        """
        sub = self._child("subList")
        if sub is None:
            return
        for p_model in sub.children:
            if local_name(p_model.tag) != "p":
                continue
            paragraph = Paragraph(p_model, self.document)
            direct_tables = [
                child
                for run in p_model.children if local_name(run.tag) == "run"
                for child in run.children if local_name(child.tag) == "tbl"
            ]
            non_table_content = False
            for run in p_model.children:
                if local_name(run.tag) != "run":
                    continue
                for child in run.children:
                    lname = local_name(child.tag)
                    if lname == "tbl":
                        continue
                    if lname == "t" and not _text_element_string(child):
                        continue
                    if lname == "linesegarray":
                        continue
                    non_table_content = True
            if direct_tables and not paragraph.text and not non_table_content:
                for table in direct_tables:
                    yield Table(table, self.document)
            else:
                yield paragraph

    def _parent_table(self) -> "Table":
        if self.document is None:
            raise RuntimeError("cell is not attached to a document")
        for table in self.document.all_tables:
            if any(cell.element_model is self.element_model for cell in table._all_cells()):
                return table
        raise RuntimeError("cell parent table could not be located")

    def merge(self, other_cell: "Cell") -> "Cell":
        """Merge the rectangular region having these cells as diagonal corners."""
        if not isinstance(other_cell, Cell):
            raise TypeError("other_cell must be a Cell")
        table = self._parent_table()
        other_table = other_cell._parent_table()
        if table.element_model is not other_table.element_model:
            raise ValueError("cells belong to different tables")
        r1, c1 = self.address
        rs1, cs1 = self.span
        r2, c2 = other_cell.address
        rs2, cs2 = other_cell.span
        start_row = min(r1, r2)
        start_col = min(c1, c2)
        end_row = max(r1 + rs1 - 1, r2 + rs2 - 1)
        end_col = max(c1 + cs1 - 1, c2 + cs2 - 1)
        return table.merge_cells(start_row, start_col, end_row, end_col)

    def add_paragraph(
        self, text: str = "", style=None, *, para_pr_id_ref: str | int = "0",
        style_id_ref: str | int = "0", char_pr_id_ref: str | int = "0",
    ) -> Paragraph:
        from .authoring import paragraph_attrs, sublist_attrs
        sub = next((c for c in self._model.children if local_name(c.tag) == "subList"), None)
        if sub is None:
            sub = ElementModel(HP + "subList", attrs=sublist_attrs())
            self._model.children.insert(0, sub)
        p = ElementModel(HP + "p", attrs=paragraph_attrs(para_pr_id_ref=para_pr_id_ref, style_id_ref=style_id_ref))
        paragraph = Paragraph(p, self.document)
        paragraph.add_run(text, char_pr_id_ref=char_pr_id_ref)
        if style is not None:
            paragraph.style = style
        sub.children.append(p)
        return paragraph

    def add_table(self, rows: int, cols: int, style=None) -> "Table":
        """Add and return a nested table after the cell's existing content."""
        width = self.width if self.width > 0 else None
        wrapper = self.add_paragraph("")
        table = wrapper.add_table(rows, cols, width=width)
        if style is not None:
            table.style = style
        # Keep an editable trailing paragraph, mirroring python-docx's cell
        # block contract and matching ordinary Hancom cell-editing behavior.
        self.add_paragraph("")
        return table



class Row(NodeProxy):
    def _physical_cells(self) -> list[Cell]:
        return [Cell(tc, self.document) for tc in self._model.children if local_name(tc.tag) == "tc"]

    @property
    def physical_cells(self) -> list[Cell]:
        """Physical HWPX cells in this row (format-level escape hatch)."""
        return self._physical_cells()

    @property
    def cells(self) -> list[Cell]:
        """Logical row cells, repeating a merged anchor for each covered grid column.

        This matches python-docx's row-cell collection semantics. Use
        ``_physical_cells()`` internally when editing the HWPX physical grid.
        """
        table = self._parent_table()
        return [table.cell(self._index, col) for col in range(table.col_count)]

    def __iter__(self):
        return iter(self.cells)

    def __len__(self) -> int:
        return len(self.cells)

    def __getitem__(self, index):
        return self.cells[index]

    def _parent_table(self) -> "Table":
        if self.document is None:
            raise RuntimeError("row is not attached to a document")
        for table in self.document.all_tables:
            if any(tr is self.element_model for tr in table._tr_models()):
                return table
        raise RuntimeError("row parent table could not be located")

    @property
    def table(self) -> "Table":
        return self._parent_table()

    @property
    def _index(self) -> int:
        table = self._parent_table()
        return next(i for i, tr in enumerate(table._tr_models()) if tr is self.element_model)

    @property
    def height(self):
        from .shared import HwpUnit
        table = self._parent_table()
        return HwpUnit(table._logical_row_heights()[self._index])

    @height.setter
    def height(self, value: int) -> None:
        self._parent_table().set_row_height(self._index, value)


class Column:
    """Logical table column proxy with python-docx-shaped width access."""

    def __init__(self, table: "Table", index: int):
        self._table = table
        self._index = int(index)

    @property
    def table(self) -> "Table":
        return self._table

    @property
    def cells(self) -> list[Cell]:
        return [self._table.cell(row, self._index) for row in range(self._table.row_count)]

    @property
    def width(self):
        from .shared import HwpUnit
        widths = self._table._logical_column_widths()
        return HwpUnit(widths[self._index])

    @width.setter
    def width(self, value: int) -> None:
        self._table.set_column_width(self._index, value)

    def __len__(self) -> int:
        return self._table.row_count

    def __iter__(self):
        return iter(self.cells)

    def __getitem__(self, index: int) -> Cell:
        return self.cells[index]



class Table(NodeProxy):
    def _tr_models(self) -> list[ElementModel]:
        return [tr for tr in self._model.children if local_name(tr.tag) == "tr"]

    def _size_node(self) -> ElementModel | None:
        return next((c for c in self._model.children if local_name(c.tag) == "sz"), None)

    @property
    def rows(self) -> list[Row]:
        return [Row(tr, self.document) for tr in self._tr_models()]

    @property
    def columns(self) -> list[Column]:
        return [Column(self, index) for index in range(self.col_count)]

    def _all_cells(self) -> list[Cell]:
        """Physical HWPX cells only; merged logical repetitions are excluded."""
        return [cell for row in self.rows for cell in row._physical_cells()]

    def cell(self, row: int, col: int) -> Cell:
        # Exact physical cell first, then the anchor of a merged range.
        for cell in self._all_cells():
            if cell.address == (row, col):
                return cell
        for cell in self._all_cells():
            r0, c0 = cell.address
            rs, cs = cell.span
            if r0 <= row < r0 + rs and c0 <= col < c0 + cs:
                return cell
        raise KeyError((row, col))

    @property
    def row_count(self) -> int:
        return int(self._model.get("rowCnt", "0") or 0)

    @property
    def col_count(self) -> int:
        return int(self._model.get("colCnt", "0") or 0)

    @property
    def alignment(self) -> str | None:
        pos=self._direct_table_child("pos"); return None if pos is None else pos.get("horzAlign")
    @alignment.setter
    def alignment(self, value: str) -> None:
        normalized=str(value).strip().upper(); aliases={"LEFT":"LEFT","CENTER":"CENTER","CENTRE":"CENTER","RIGHT":"RIGHT"}
        if normalized not in aliases: raise ValueError("table alignment must be LEFT/CENTER/RIGHT")
        pos=self._direct_table_child("pos")
        if pos is None:
            pos=ElementModel(HP+"pos", attrs=[("treatAsChar","1"),("affectLSpacing","0"),("flowWithText","1"),("allowOverlap","0"),("holdAnchorAndSO","0"),("vertRelTo","PARA"),("horzRelTo","COLUMN"),("vertAlign","TOP"),("horzAlign",aliases[normalized]),("vertOffset","0"),("horzOffset","0")]); self._model.children.insert(1,pos)
        else: pos.set("horzAlign",aliases[normalized])

    def _direct_table_child(self, name: str) -> ElementModel | None:
        return next((c for c in self._model.children if local_name(c.tag)==name), None)

    @property
    def autofit(self) -> bool:
        return self._model.get("noAdjust","0") != "1"
    @autofit.setter
    def autofit(self, value: bool) -> None:
        self._model.set("noAdjust", "0" if value else "1")

    @property
    def style(self) -> str:
        # HWPX tables reference borderFill rather than OOXML tableStyle.
        return self._model.get("borderFillIDRef","0") or "0"
    @style.setter
    def style(self, value) -> None:
        if isinstance(value, str) and value.strip().casefold() in {"table grid","표 격자","grid"}:
            if self.document is None: raise RuntimeError("table is detached")
            value=self.document.styles.ensure_border_fill(base_border_fill_id="1", color="#000000", width="0.12 mm", border_type="SOLID")
        self._model.set("borderFillIDRef", str(value))

    def _coverage(self) -> dict[tuple[int, int], Cell]:
        coverage: dict[tuple[int, int], Cell] = {}
        for cell in self._all_cells():
            r0, c0 = cell.address
            rs, cs = cell.span
            if rs <= 0 or cs <= 0:
                raise ValueError(f"invalid cell span at {cell.address}: {cell.span}")
            for r in range(r0, r0 + rs):
                for c in range(c0, c0 + cs):
                    if not (0 <= r < self.row_count and 0 <= c < self.col_count):
                        raise ValueError(f"cell span extends outside table: {cell.address} {cell.span}")
                    key = (r, c)
                    if key in coverage and coverage[key].element_model is not cell.element_model:
                        raise ValueError(f"overlapping merged cells at {key}")
                    coverage[key] = cell
        expected = {(r, c) for r in range(self.row_count) for c in range(self.col_count)}
        missing = expected - set(coverage)
        if missing:
            raise ValueError(f"table has uncovered logical cells: {sorted(missing)[:5]}")
        return coverage

    def _logical_column_widths(self) -> list[int]:
        from .authoring import distribute_size
        self._coverage()
        widths = [0] * self.col_count
        # A 1-column physical cell is direct evidence of that logical column's
        # width. Prefer those before estimating widths from merged cells.
        for cell in self._all_cells():
            _r, c0 = cell.address
            _rs, cs = cell.span
            if cs == 1 and 0 <= c0 < len(widths):
                widths[c0] = cell.width
        # Fill any column that only occurs inside merged cells by distributing
        # the merged physical width across its still-unknown logical columns.
        for cell in self._all_cells():
            _r, c0 = cell.address
            _rs, cs = cell.span
            if cs <= 1:
                continue
            parts = distribute_size(cell.width, cs)
            for offset, value in enumerate(parts):
                c = c0 + offset
                if c < len(widths) and widths[c] == 0:
                    widths[c] = value
        size = self._size_node()
        total = 0 if size is None else int(size.get("width", "0") or 0)
        fallback = distribute_size(total, self.col_count) if self.col_count else []
        return [value or (fallback[i] if i < len(fallback) else 0) for i, value in enumerate(widths)]

    def set_column_width(self, index: int, value: int) -> None:
        """Set one logical column width while preserving merged-cell spans."""
        if not 0 <= int(index) < self.col_count:
            raise IndexError("column index out of range")
        new_width = max(int(value), 0)
        widths = self._logical_column_widths()
        old_width = widths[index]
        delta = new_width - old_width
        if delta == 0:
            return
        self._coverage()
        touched: set[int] = set()
        for cell in self._all_cells():
            _r0, c0 = cell.address
            _rs, cs = cell.span
            if c0 <= index < c0 + cs and id(cell.element_model) not in touched:
                cell.width = max(cell.width + delta, 0)
                touched.add(id(cell.element_model))
        size = self._size_node()
        if size is not None:
            total = int(size.get("width", "0") or 0)
            size.set("width", str(max(total + delta, 0)))

    def _logical_row_heights(self) -> list[int]:
        from .authoring import distribute_size
        self._coverage()
        heights = [0] * self.row_count
        # A 1-row physical cell is direct evidence of that logical row's
        # height. Prefer those before estimating from vertically merged cells.
        for cell in self._all_cells():
            r0, _c = cell.address
            rs, _cs = cell.span
            if rs == 1 and 0 <= r0 < len(heights):
                heights[r0] = cell.height
        # Fill rows that only occur inside a vertical merge by distributing the
        # merged physical height over still-unknown logical rows.
        for cell in self._all_cells():
            r0, _c = cell.address
            rs, _cs = cell.span
            if rs <= 1:
                continue
            parts = distribute_size(cell.height, rs)
            for offset, value in enumerate(parts):
                r = r0 + offset
                if r < len(heights) and heights[r] == 0:
                    heights[r] = value
        size = self._size_node()
        total = 0 if size is None else int(size.get("height", "0") or 0)
        fallback = distribute_size(total, self.row_count) if self.row_count else []
        return [value or (fallback[i] if i < len(fallback) else 0) for i, value in enumerate(heights)]

    def set_row_height(self, index: int, value: int) -> None:
        """Set one logical row height while preserving vertical merged spans."""
        if not 0 <= int(index) < self.row_count:
            raise IndexError("row index out of range")
        new_height = max(int(value), 0)
        heights = self._logical_row_heights()
        old_height = heights[index]
        delta = new_height - old_height
        if delta == 0:
            return
        self._coverage()
        touched: set[int] = set()
        for cell in self._all_cells():
            r0, _c0 = cell.address
            rs, _cs = cell.span
            if r0 <= index < r0 + rs and id(cell.element_model) not in touched:
                cell.height = max(cell.height + delta, 0)
                touched.add(id(cell.element_model))
        size = self._size_node()
        if size is not None:
            total = int(size.get("height", "0") or 0)
            size.set("height", str(max(total + delta, 0)))

    @staticmethod
    def _clear_cell_text(model: ElementModel) -> None:
        for node in model.iter():
            if local_name(node.tag) == "t":
                node.text = ""
        model.set("dirty", "0")

    def _clone_cell_for(self, template: Cell, row: int, col: int, width: int, height: int) -> ElementModel:
        from .authoring import paragraph_id
        cloned = ElementModel.from_dict(template.element_model.to_dict())
        cell = Cell(cloned, self.document)
        cell._set_address(row, col)
        cell._set_span(1, 1)
        cell.width = max(int(width), 0)
        cell.height = max(int(height), 0)

        # A merged anchor may carry several paragraphs (merged-away cell text).
        # A newly appended ordinary cell must start as one blank paragraph, so
        # retain formatting references from the first paragraph/run but not its
        # semantic content or layout cache.
        sub = next((c for c in cloned.children if local_name(c.tag) == "subList"), None)
        if sub is not None:
            first_p = next((c for c in sub.children if local_name(c.tag) == "p"), None)
            if first_p is not None:
                p_attrs = list(first_p.attrs)
                p = ElementModel(HP + "p", attrs=p_attrs)
                p.set("id", paragraph_id())
                first_run = next((c for c in first_p.children if local_name(c.tag) == "run"), None)
                char_ref = "0" if first_run is None else (first_run.get("charPrIDRef") or "0")
                run = ElementModel(HP + "run", attrs=[("charPrIDRef", char_ref)])
                run.children.append(ElementModel(HP + "t", text=""))
                p.children.append(run)
                sub.children = [p]
        self._clear_cell_text(cloned)
        return cloned

    def _insert_tr_model(self, index: int, tr: ElementModel) -> None:
        trs = self._tr_models()
        if index < len(trs):
            at = self._model.children.index(trs[index])
        elif trs:
            at = self._model.children.index(trs[-1]) + 1
        else:
            at = len(self._model.children)
        self._model.children.insert(at, tr)

    @staticmethod
    def _sort_row_cells(tr: ElementModel) -> None:
        cells = [c for c in tr.children if local_name(c.tag) == "tc"]
        other = [c for c in tr.children if local_name(c.tag) != "tc"]
        def col(cell: ElementModel) -> int:
            addr = next((c for c in cell.children if local_name(c.tag) == "cellAddr"), None)
            return int(addr.get("colAddr", "0") or 0) if addr is not None else 0
        tr.children = sorted(cells, key=col) + other

    def insert_row(self, index: int, *, height: int | None = None) -> Row:
        """Insert a logical row and extend vertical merges that cross it."""
        if not 0 <= index <= self.row_count:
            raise IndexError("row insertion index out of range")
        if self.row_count <= 0 or self.col_count <= 0:
            raise ValueError("table has no cell template")
        coverage = self._coverage()
        widths = self._logical_column_widths()
        heights = self._logical_row_heights()
        template_row = min(index, self.row_count - 1)
        templates = [coverage[(template_row, c)] for c in range(self.col_count)]
        if height is None:
            if index < len(heights):
                height = heights[index]
            else:
                height = heights[-1] if heights else 0
        new_height = max(int(height), 0)

        covered_cols: set[int] = set()
        for cell in self._all_cells():
            r0, c0 = cell.address
            rs, cs = cell.span
            if r0 >= index:
                cell._set_address(r0 + 1, c0)
            elif r0 < index < r0 + rs:
                cell._set_span(rs + 1, cs)
                cell.height = cell.height + new_height
                covered_cols.update(range(c0, c0 + cs))

        tr = ElementModel(HP + "tr")
        for c in range(self.col_count):
            if c in covered_cols:
                continue
            tr.children.append(self._clone_cell_for(templates[c], index, c, widths[c], new_height))
        self._sort_row_cells(tr)
        self._insert_tr_model(index, tr)
        self._model.set("rowCnt", str(self.row_count + 1))
        size = self._size_node()
        if size is not None:
            size.set("height", str(int(size.get("height", "0") or 0) + new_height))
        self._coverage()
        return Row(tr, self.document)

    def add_row(self, *, height: int | None = None) -> Row:
        return self.insert_row(self.row_count, height=height)

    def insert_column(self, index: int, *, width: int | None = None) -> list[Cell]:
        """Insert a logical column and extend horizontal merges that cross it."""
        if not 0 <= index <= self.col_count:
            raise IndexError("column insertion index out of range")
        if self.row_count <= 0 or self.col_count <= 0:
            raise ValueError("table has no cell template")
        coverage = self._coverage()
        widths = self._logical_column_widths()
        heights = self._logical_row_heights()
        template_col = min(index, self.col_count - 1)
        templates = [coverage[(r, template_col)] for r in range(self.row_count)]
        if width is None:
            if index < len(widths):
                width = widths[index]
            else:
                width = widths[-1] if widths else 0
        new_width = max(int(width), 0)

        covered_rows: set[int] = set()
        for cell in self._all_cells():
            r0, c0 = cell.address
            rs, cs = cell.span
            if c0 >= index:
                cell._set_address(r0, c0 + 1)
            elif c0 < index < c0 + cs:
                cell._set_span(rs, cs + 1)
                cell.width = cell.width + new_width
                covered_rows.update(range(r0, r0 + rs))

        created: list[Cell] = []
        trs = self._tr_models()
        for r, tr in enumerate(trs):
            if r in covered_rows:
                self._sort_row_cells(tr)
                continue
            cloned = self._clone_cell_for(templates[r], r, index, new_width, heights[r])
            tr.children.append(cloned)
            self._sort_row_cells(tr)
            created.append(Cell(cloned, self.document))
        self._model.set("colCnt", str(self.col_count + 1))
        size = self._size_node()
        if size is not None:
            size.set("width", str(int(size.get("width", "0") or 0) + new_width))
        self._coverage()
        return created

    def add_column(self, *, width: int | None = None) -> list[Cell]:
        return self.insert_column(self.col_count, width=width)

    def delete_row(self, index: int) -> None:
        """Delete a logical row, shrinking or relocating merged anchors as needed."""
        if self.row_count <= 1:
            raise ValueError("a table must keep at least one row")
        if not 0 <= index < self.row_count:
            raise IndexError("row deletion index out of range")
        self._coverage()
        heights = self._logical_row_heights()
        removed_height = heights[index]
        trs = self._tr_models()
        target_tr = trs[index]
        next_tr = trs[index + 1] if index + 1 < len(trs) else None
        moves: list[ElementModel] = []
        for cell in list(self._all_cells()):
            r0, c0 = cell.address
            rs, cs = cell.span
            if r0 == index:
                if rs > 1:
                    cell._set_span(rs - 1, cs)
                    cell.height = max(cell.height - removed_height, 0)
                    # after deletion, the old next row becomes this same index
                    cell._set_address(index, c0)
                    moves.append(cell.element_model)
            elif r0 < index < r0 + rs:
                cell._set_span(rs - 1, cs)
                cell.height = max(cell.height - removed_height, 0)
            elif r0 > index:
                cell._set_address(r0 - 1, c0)
        if moves and next_tr is None:
            raise ValueError("cannot relocate merged cells from the final row")
        for model in moves:
            if model in target_tr.children:
                target_tr.children.remove(model)
            next_tr.children.append(model)
        self._model.children.remove(target_tr)
        if next_tr is not None:
            self._sort_row_cells(next_tr)
        self._model.set("rowCnt", str(self.row_count - 1))
        size = self._size_node()
        if size is not None:
            size.set("height", str(max(int(size.get("height", "0") or 0) - removed_height, 0)))
        self._coverage()

    def delete_column(self, index: int) -> None:
        """Delete a logical column while preserving surrounding merge geometry."""
        if self.col_count <= 1:
            raise ValueError("a table must keep at least one column")
        if not 0 <= index < self.col_count:
            raise IndexError("column deletion index out of range")
        self._coverage()
        widths = self._logical_column_widths()
        removed_width = widths[index]
        remove_models: set[int] = set()
        for cell in list(self._all_cells()):
            r0, c0 = cell.address
            rs, cs = cell.span
            if c0 == index:
                if cs == 1:
                    remove_models.add(id(cell.element_model))
                else:
                    cell._set_span(rs, cs - 1)
                    cell.width = max(cell.width - removed_width, 0)
                    cell._set_address(r0, index)
            elif c0 < index < c0 + cs:
                cell._set_span(rs, cs - 1)
                cell.width = max(cell.width - removed_width, 0)
            elif c0 > index:
                cell._set_address(r0, c0 - 1)
        for tr in self._tr_models():
            tr.children[:] = [c for c in tr.children if id(c) not in remove_models]
            self._sort_row_cells(tr)
        self._model.set("colCnt", str(self.col_count - 1))
        size = self._size_node()
        if size is not None:
            size.set("width", str(max(int(size.get("width", "0") or 0) - removed_width, 0)))
        self._coverage()

    def insert_rows(self, index: int, count: int = 1, *, height: int | None = None) -> list[Row]:
        if count < 0: raise ValueError("count must be non-negative")
        return [self.insert_row(index+i, height=height) for i in range(count)]

    def delete_rows(self, index: int, count: int = 1) -> None:
        if count < 0: raise ValueError("count must be non-negative")
        if index < 0 or index + count > self.row_count: raise IndexError("row range out of range")
        for _ in range(count): self.delete_row(index)

    def insert_columns(self, index: int, count: int = 1, *, width: int | None = None) -> list[list[Cell]]:
        if count < 0: raise ValueError("count must be non-negative")
        return [self.insert_column(index+i, width=width) for i in range(count)]

    def delete_columns(self, index: int, count: int = 1) -> None:
        if count < 0: raise ValueError("count must be non-negative")
        if index < 0 or index + count > self.col_count: raise IndexError("column range out of range")
        for _ in range(count): self.delete_column(index)

    def merge_cells(self, start_row: int, start_col: int, end_row: int, end_col: int) -> Cell:
        """Merge a rectangular range and return its top-left anchor cell."""
        if min(start_row, start_col, end_row, end_col) < 0:
            raise ValueError("cell coordinates must be non-negative")
        if end_row < start_row or end_col < start_col:
            raise ValueError("end cell must be at or below/right of start cell")
        targets: list[Cell] = []
        for r in range(start_row, end_row + 1):
            for c in range(start_col, end_col + 1):
                cell = self.cell(r, c)
                if cell.address != (r, c) or cell.span != (1, 1):
                    raise ValueError("merge_cells does not accept a range crossing an existing merged cell")
                targets.append(cell)
        anchor = self.cell(start_row, start_col)
        widths = [self.cell(start_row, c).width for c in range(start_col, end_col + 1)]
        heights = [self.cell(r, start_col).height for r in range(start_row, end_row + 1)]
        texts = [cell.text for cell in targets if cell.text]
        # Remove non-anchor physical cells from their row elements.
        for cell in targets:
            if cell.element_model is anchor.element_model:
                continue
            for tr in self._tr_models():
                if any(child is cell.element_model for child in tr.children):
                    tr.children.remove(cell.element_model)
                    break
        anchor._set_span(end_row - start_row + 1, end_col - start_col + 1)
        anchor.width = sum(widths)
        anchor.height = sum(heights)
        if texts:
            anchor.text = texts[0]
            for extra in texts[1:]:
                anchor.add_paragraph(extra)
        return anchor


class Shape(NodeProxy):
    def _direct(self, name: str) -> ElementModel | None:
        return next((c for c in self._model.children if local_name(c.tag) == name), None)

    def _pos(self) -> ElementModel:
        pos = self._direct("pos")
        if pos is None:
            pos = ElementModel(HP + "pos", attrs=[
                ("treatAsChar", "1"), ("affectLSpacing", "0"), ("flowWithText", "1"),
                ("allowOverlap", "0"), ("holdAnchorAndSO", "0"), ("vertRelTo", "PARA"),
                ("horzRelTo", "COLUMN"), ("vertAlign", "TOP"), ("horzAlign", "LEFT"),
                ("vertOffset", "0"), ("horzOffset", "0"),
            ])
            self._model.children.append(pos)
        return pos

    @property
    def width(self) -> int | None:
        sz = self._direct("sz")
        raw = None if sz is None else sz.get("width")
        return None if raw is None else int(raw)

    @width.setter
    def width(self, value: int) -> None:
        self.resize(width=value)

    @property
    def height(self) -> int | None:
        sz = self._direct("sz")
        raw = None if sz is None else sz.get("height")
        return None if raw is None else int(raw)

    @height.setter
    def height(self, value: int) -> None:
        self.resize(height=value)

    @property
    def text_wrap(self) -> str | None:
        return self._model.get("textWrap")

    @text_wrap.setter
    def text_wrap(self, value: str) -> None:
        self._model.set("textWrap", str(value).upper())

    @property
    def treat_as_char(self) -> bool:
        return self._pos().get("treatAsChar", "1") == "1"

    @treat_as_char.setter
    def treat_as_char(self, value: bool) -> None:
        pos = self._pos()
        flag = bool(value)
        pos.set("treatAsChar", "1" if flag else "0")
        pos.set("flowWithText", "1" if flag else "0")
        pos.set("allowOverlap", "0" if flag else "1")

    @property
    def horizontal_alignment(self) -> str | None:
        return self._pos().get("horzAlign")

    @horizontal_alignment.setter
    def horizontal_alignment(self, value: str) -> None:
        self._pos().set("horzAlign", str(value).upper())

    @property
    def vertical_alignment(self) -> str | None:
        return self._pos().get("vertAlign")

    @vertical_alignment.setter
    def vertical_alignment(self, value: str) -> None:
        self._pos().set("vertAlign", str(value).upper())

    @property
    def horizontal_offset(self) -> int:
        return int(self._pos().get("horzOffset", "0") or 0)

    @horizontal_offset.setter
    def horizontal_offset(self, value: int) -> None:
        self._pos().set("horzOffset", str(max(int(value), 0)))

    @property
    def vertical_offset(self) -> int:
        return int(self._pos().get("vertOffset", "0") or 0)

    @vertical_offset.setter
    def vertical_offset(self, value: int) -> None:
        self._pos().set("vertOffset", str(max(int(value), 0)))

    def set_position(
        self, *, treat_as_char: bool | None = None, horizontal_alignment: str | None = None,
        vertical_alignment: str | None = None, horizontal_offset: int | None = None,
        vertical_offset: int | None = None, horizontal_relative_to: str | None = None,
        vertical_relative_to: str | None = None, text_wrap: str | None = None,
    ) -> "Shape":
        pos = self._pos()
        if treat_as_char is not None:
            self.treat_as_char = treat_as_char
        if horizontal_alignment is not None:
            self.horizontal_alignment = horizontal_alignment
        if vertical_alignment is not None:
            self.vertical_alignment = vertical_alignment
        if horizontal_offset is not None:
            self.horizontal_offset = horizontal_offset
        if vertical_offset is not None:
            self.vertical_offset = vertical_offset
        if horizontal_relative_to is not None:
            pos.set("horzRelTo", str(horizontal_relative_to).upper())
        if vertical_relative_to is not None:
            pos.set("vertRelTo", str(vertical_relative_to).upper())
        if text_wrap is not None:
            self.text_wrap = text_wrap
        return self

    def _resize_common(self, width: int, height: int) -> None:
        for name in ("orgSz", "curSz", "sz"):
            node = self._direct(name)
            if node is not None:
                node.set("width", str(width))
                node.set("height", str(height))
        rotation = self._direct("rotationInfo")
        if rotation is not None:
            rotation.set("centerX", str(width // 2))
            rotation.set("centerY", str(height // 2))

    def resize(self, *, width: int | None = None, height: int | None = None) -> "Shape":
        current_w, current_h = self.width, self.height
        if current_w is None or current_h is None:
            raise ValueError("shape has no size")
        w = current_w if width is None else max(int(width), 0)
        h = current_h if height is None else max(int(height), 0)
        self._resize_common(w, h)
        self._resize_geometry(w, h)
        return self

    def _resize_geometry(self, width: int, height: int) -> None:
        pass


class Rectangle(Shape):
    @property
    def paragraphs(self) -> list[Paragraph]:
        result: list[Paragraph] = []
        for node in self._model.children:
            if local_name(node.tag) != "drawText":
                continue
            for sub in node.children:
                if local_name(sub.tag) == "subList":
                    result.extend(Paragraph(p, self.document) for p in sub.children if local_name(p.tag) == "p")
        return result

    @property
    def text(self) -> str:
        return "\n".join(p.text for p in self.paragraphs)

    def _resize_geometry(self, width: int, height: int) -> None:
        points = {local_name(c.tag): c for c in self._model.children if local_name(c.tag) in {"pt0", "pt1", "pt2", "pt3"}}
        coords = {"pt0": (0, 0), "pt1": (width, 0), "pt2": (width, height), "pt3": (0, height)}
        for name, (x, y) in coords.items():
            if name in points:
                points[name].set("x", str(x)); points[name].set("y", str(y))
        draw = self._direct("drawText")
        if draw is not None:
            draw.set("lastWidth", str(width))

    def add_paragraph(
        self, text: str = "", *, para_pr_id_ref: str | int = "0", char_pr_id_ref: str | int = "0"
    ) -> Paragraph:
        from .authoring import paragraph_attrs, sublist_attrs
        draw = next((c for c in self._model.children if local_name(c.tag) == "drawText"), None)
        if draw is None:
            draw = ElementModel(HP + "drawText", attrs=[("lastWidth", str(self.width or 0)), ("name", ""), ("editable", "0")])
            sub = ElementModel(HP + "subList", attrs=sublist_attrs())
            draw.children.extend([sub, ElementModel(HP + "textMargin", attrs=[("left","283"),("right","283"),("top","283"),("bottom","283")])])
            insert_at = next((i for i,c in enumerate(self._model.children) if local_name(c.tag) in {"pt0","pt1","pt2","pt3"}), len(self._model.children))
            self._model.children.insert(insert_at, draw)
        else:
            sub = next((c for c in draw.children if local_name(c.tag) == "subList"), None)
            if sub is None:
                sub = ElementModel(HP + "subList", attrs=sublist_attrs())
                draw.children.insert(0, sub)
        p = ElementModel(HP + "p", attrs=paragraph_attrs(para_pr_id_ref=para_pr_id_ref))
        paragraph = Paragraph(p, self.document)
        paragraph.add_run(text, char_pr_id_ref=char_pr_id_ref)
        sub.children.append(p)
        return paragraph


class Picture(Shape):
    @property
    def binary_item_id_ref(self) -> str | None:
        for n in self._model.children:
            if local_name(n.tag) == "img":
                return n.get("binaryItemIDRef")
        return None

    @property
    def size(self) -> tuple[int | None, int | None]:
        return self.width, self.height

    @property
    def crop_box(self) -> tuple[float,float,float,float]:
        clip=self._direct("imgClip"); dim=self._direct("imgDim")
        if clip is None or dim is None: return (0.0,0.0,0.0,0.0)
        w=max(int(dim.get("dimwidth","1") or 1),1); h=max(int(dim.get("dimheight","1") or 1),1)
        return (int(clip.get("left","0") or 0)/w, int(clip.get("top","0") or 0)/h, 1-int(clip.get("right",str(w)) or w)/w, 1-int(clip.get("bottom",str(h)) or h)/h)

    def crop(self, *, left: float=0, top: float=0, right: float=0, bottom: float=0) -> "Picture":
        vals=[left,top,right,bottom]
        if any(v<0 or v>=1 for v in vals) or left+right>=1 or top+bottom>=1: raise ValueError("crop fractions must leave a positive image area")
        dim=self._direct("imgDim")
        if dim is None:
            dim=ElementModel(HP+"imgDim", attrs=[("dimwidth",str(self.width or 1)),("dimheight",str(self.height or 1))]); self._model.children.append(dim)
        w=max(int(dim.get("dimwidth","1") or 1),1); h=max(int(dim.get("dimheight","1") or 1),1)
        clip=self._direct("imgClip")
        if clip is None:
            clip=ElementModel(HP+"imgClip"); self._model.children.append(clip)
        clip.set("left",str(round(w*left))); clip.set("top",str(round(h*top))); clip.set("right",str(round(w*(1-right)))); clip.set("bottom",str(round(h*(1-bottom))))
        return self

    @property
    def brightness(self) -> int:
        img=next((n for n in self._model.children if local_name(n.tag)=="img"),None); return int((img.get("bright") if img else "0") or 0)
    @brightness.setter
    def brightness(self, value: int) -> None:
        if not -100 <= int(value) <= 100: raise ValueError("brightness must be between -100 and 100")
        img=next((n for n in self._model.children if local_name(n.tag)=="img"),None)
        if img is not None: img.set("bright",str(int(value)))

    @property
    def contrast(self) -> int:
        img=next((n for n in self._model.children if local_name(n.tag)=="img"),None); return int((img.get("contrast") if img else "0") or 0)
    @contrast.setter
    def contrast(self, value: int) -> None:
        if not -100 <= int(value) <= 100: raise ValueError("contrast must be between -100 and 100")
        img=next((n for n in self._model.children if local_name(n.tag)=="img"),None)
        if img is not None: img.set("contrast",str(int(value)))

    def _resize_geometry(self, width: int, height: int) -> None:
        rect = self._direct("imgRect")
        if rect is not None:
            points = {local_name(c.tag): c for c in rect.children if local_name(c.tag) in {"pt0","pt1","pt2","pt3"}}
            coords = {"pt0": (0,0), "pt1": (width,0), "pt2": (width,height), "pt3": (0,height)}
            for name, (x,y) in coords.items():
                if name in points:
                    points[name].set("x", str(x)); points[name].set("y", str(y))
        clip = self._direct("imgClip")
        dim = self._direct("imgDim")
        if clip is not None and dim is not None:
            old_w=max(int(dim.get("dimwidth","1") or 1),1); old_h=max(int(dim.get("dimheight","1") or 1),1)
            l=int(clip.get("left","0") or 0)/old_w; t=int(clip.get("top","0") or 0)/old_h
            r=1-int(clip.get("right",str(old_w)) or old_w)/old_w; b=1-int(clip.get("bottom",str(old_h)) or old_h)/old_h
            clip.set("left",str(round(width*l))); clip.set("top",str(round(height*t))); clip.set("right",str(round(width*(1-r)))); clip.set("bottom",str(round(height*(1-b))))
        elif clip is not None:
            clip.set("left", "0"); clip.set("top", "0"); clip.set("right", str(width)); clip.set("bottom", str(height))
        if dim is not None:
            dim.set("dimwidth", str(width)); dim.set("dimheight", str(height))

