from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import math
from typing import TYPE_CHECKING, Iterable, Iterator

from .model import ElementModel, HH, HC, HP, local_name
from .shared import Length, HwpUnit
from .enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER
from .enum.style import WD_STYLE_TYPE
from .errors import HwpxValueError, HwpxUnsupportedError

if TYPE_CHECKING:
    from .document import Document
    from .model import Run, Paragraph, Cell

_FONT_LANGS = {
    "HANGUL": "hangul",
    "LATIN": "latin",
    "HANJA": "hanja",
    "JAPANESE": "japanese",
    "OTHER": "other",
    "SYMBOL": "symbol",
    "USER": "user",
}
_BORDER_SIDES = ("leftBorder", "rightBorder", "topBorder", "bottomBorder")
_HWPUNITCHAR_NS = "http://www.hancom.co.kr/hwpml/2016/HwpUnitChar"
_TAB_ALIGN_TO_HWPX = {
    WD_TAB_ALIGNMENT.LEFT: "LEFT", WD_TAB_ALIGNMENT.CENTER: "CENTER",
    WD_TAB_ALIGNMENT.RIGHT: "RIGHT", WD_TAB_ALIGNMENT.DECIMAL: "DECIMAL",
}
_TAB_ALIGN_FROM_HWPX = {v: k for k, v in _TAB_ALIGN_TO_HWPX.items()}
_TAB_LEADER_TO_HWPX = {
    WD_TAB_LEADER.SPACES: "NONE", WD_TAB_LEADER.DOTS: "DOT",
    WD_TAB_LEADER.DASHES: "DASH", WD_TAB_LEADER.LINES: "SOLID",
    WD_TAB_LEADER.HEAVY: "SOLID", WD_TAB_LEADER.MIDDLE_DOT: "DOT",
}
_TAB_LEADER_FROM_HWPX = {
    "NONE": WD_TAB_LEADER.SPACES, "DOT": WD_TAB_LEADER.DOTS,
    "DASH": WD_TAB_LEADER.DASHES, "SOLID": WD_TAB_LEADER.LINES,
    "DASH_DOT": WD_TAB_LEADER.DASHES, "LONG_DASH": WD_TAB_LEADER.DASHES,
}


def _norm_color(value: str) -> str:
    value = value.strip()
    if not value.startswith("#"):
        value = "#" + value
    if len(value) != 7 or any(c not in "0123456789abcdefABCDEF" for c in value[1:]):
        raise ValueError(f"color must be #RRGGBB: {value!r}")
    return value.upper()


def _font_size_height(value) -> int:
    """Normalize a public font-size value to HWPX 1/100-point units.

    PyWPDoc's own :class:`Length` values are stored in HWPUNIT, while
    python-docx length objects are EMU-backed integers. Treating a foreign
    length as a plain number multiplies EMUs by 100 and can produce absurd
    HWPX ``charPr@height`` values (for example ``Pt(14)`` -> 17780000).
    Prefer an explicit ``.pt`` physical-value accessor when one is present.
    """
    if isinstance(value, Length):
        points = float(value.pt)
    elif hasattr(value, "pt"):
        try:
            points = float(value.pt)
        except (TypeError, ValueError, OverflowError) as exc:
            raise HwpxValueError(
                "font size .pt value must be numeric",
                code="font-size-invalid",
                context={"type": type(value).__name__},
            ) from exc
    elif isinstance(value, bool):
        raise HwpxValueError(
            "font size must be a positive point value",
            code="font-size-invalid",
            context={"value": value},
        )
    elif isinstance(value, (int, float)):
        points = float(value)
    else:
        raise HwpxValueError(
            "font size must be numeric or expose a numeric .pt value",
            code="font-size-invalid",
            context={"type": type(value).__name__},
        )
    if not math.isfinite(points) or points <= 0:
        raise HwpxValueError(
            "font size must be a finite positive point value",
            code="font-size-invalid",
            context={"points": points},
        )
    return round(points * 100)


def _clone(node: ElementModel) -> ElementModel:
    return ElementModel.from_dict(node.to_dict())


def _signature(node: ElementModel, *, ignore_id: bool = False):
    attrs = tuple((k, v) for k, v in node.attrs if not (ignore_id and k == "id"))
    return (
        node.tag,
        attrs,
        node.text,
        node.tail,
        tuple(_signature(c) for c in node.children),
    )


def _children(node: ElementModel, name: str) -> list[ElementModel]:
    return [c for c in node.children if local_name(c.tag) == name]


def _child(node: ElementModel, name: str) -> ElementModel | None:
    return next((c for c in node.children if local_name(c.tag) == name), None)


def _desc(node: ElementModel, name: str) -> list[ElementModel]:
    return [c for c in node.iter() if c is not node and local_name(c.tag) == name]


def _first_desc(node: ElementModel, name: str) -> ElementModel | None:
    return next((c for c in node.iter() if c is not node and local_name(c.tag) == name), None)


def _set_attr(node: ElementModel, name: str, value: str | int) -> None:
    node.set(name, str(value))


def _remove_children(node: ElementModel, name: str) -> None:
    node.children[:] = [c for c in node.children if local_name(c.tag) != name]


def _insert_char_child(node: ElementModel, child: ElementModel) -> None:
    order = {
        "fontRef": 10, "ratio": 20, "spacing": 30, "relSz": 40, "offset": 50,
        "bold": 60, "italic": 70, "underline": 80, "strikeout": 90,
        "outline": 100, "shadow": 110, "emboss": 120, "engrave": 130,
        "supscript": 140, "subscript": 140,
    }
    target = order.get(local_name(child.tag), 1000)
    idx = len(node.children)
    for i, existing in enumerate(node.children):
        if order.get(local_name(existing.tag), 1000) > target:
            idx = i
            break
    node.children.insert(idx, child)


def _ensure_char_child(node: ElementModel, name: str, attrs: dict[str, str] | None = None) -> ElementModel:
    found = _child(node, name)
    if found is not None:
        return found
    found = ElementModel(HH + name, attrs=list((attrs or {}).items()))
    _insert_char_child(node, found)
    return found


def _container(header: ElementModel, name: str) -> ElementModel:
    found = _first_desc(header, name)
    if found is None:
        raise ValueError(f"header is missing {name}")
    return found


def _by_id(container: ElementModel, child_name: str, identifier: str | int | None) -> ElementModel | None:
    if identifier is None:
        return None
    wanted = str(identifier).strip()
    for node in container.children:
        if local_name(node.tag) == child_name and (node.get("id") or "").strip() == wanted:
            return node
    try:
        wanted_num = int(wanted)
    except ValueError:
        return None
    for node in container.children:
        if local_name(node.tag) != child_name:
            continue
        try:
            if int(node.get("id") or "") == wanted_num:
                return node
        except ValueError:
            pass
    return None


def _next_id(container: ElementModel, child_name: str) -> str:
    ids: list[int] = []
    for node in container.children:
        if local_name(node.tag) != child_name:
            continue
        try:
            ids.append(int(node.get("id") or ""))
        except ValueError:
            pass
    return str(max(ids, default=-1) + 1)


def _update_count(container: ElementModel, child_name: str, attr: str = "itemCnt") -> None:
    container.set(attr, str(sum(local_name(c.tag) == child_name for c in container.children)))


def _node_numeric_value(node: ElementModel | None) -> int | None:
    if node is None:
        return None
    raw = node.get("value")
    if raw is None:
        raw = node.text
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


class Style:
    """A named HWPX style definition.

    v0.7 makes style objects live/mutable like ``python-docx`` styles: the
    style owns references to shared charPr/paraPr definitions and mutations
    use the same copy-on-write registries as runs and paragraphs.
    """

    def __init__(self, model: ElementModel, styles: "Styles | None" = None):
        self._model = model
        self._styles = styles

    @property
    def element_model(self) -> ElementModel:
        return self._model

    @property
    def id(self) -> str:
        return self._model.get("id", "0") or "0"

    @property
    def type(self) -> str | None:
        return self._model.get("type")

    @property
    def style_type(self) -> WD_STYLE_TYPE | None:
        raw = (self.type or "").upper()
        if raw in {"PARA", "PARAGRAPH"}:
            return WD_STYLE_TYPE.PARAGRAPH
        if raw in {"CHAR", "CHARACTER"}:
            return WD_STYLE_TYPE.CHARACTER
        return None

    @property
    def name(self) -> str | None:
        return self._model.get("name")

    @name.setter
    def name(self, value: str) -> None:
        value = str(value).strip()
        if not value:
            raise HwpxValueError("style name must not be empty", code="style-name-empty")
        self._model.set("name", value)

    @property
    def eng_name(self) -> str | None:
        return self._model.get("engName")

    @eng_name.setter
    def eng_name(self, value: str | None) -> None:
        if value is None:
            self._model.attrs[:] = [(k,v) for k,v in self._model.attrs if k != "engName"]
        else:
            self._model.set("engName", str(value))

    @property
    def para_pr_id_ref(self) -> str | None:
        return self._model.get("paraPrIDRef")

    @para_pr_id_ref.setter
    def para_pr_id_ref(self, value: str | int) -> None:
        self._model.set("paraPrIDRef", str(value))

    @property
    def char_pr_id_ref(self) -> str | None:
        return self._model.get("charPrIDRef")

    @char_pr_id_ref.setter
    def char_pr_id_ref(self, value: str | int) -> None:
        self._model.set("charPrIDRef", str(value))

    @property
    def next_style_id_ref(self) -> str | None:
        return self._model.get("nextStyleIDRef")

    @next_style_id_ref.setter
    def next_style_id_ref(self, value: str | int | None) -> None:
        if value is None:
            self._model.attrs[:] = [(k,v) for k,v in self._model.attrs if k != "nextStyleIDRef"]
        else:
            self._model.set("nextStyleIDRef", str(value))

    @property
    def next_paragraph_style(self) -> "Style":
        """Style automatically applied to a following paragraph.

        HWPX stores this directly as ``hh:style/@nextStyleIDRef``. As in
        python-docx, an absent, invalid, non-paragraph, or self reference
        resolves to this style itself.
        """
        if self._styles is None:
            raise RuntimeError("style is detached from a Styles collection")
        ref = self.next_style_id_ref
        if ref is None:
            return self
        target = self._styles.get(ref)
        if target is None or target.style_type != WD_STYLE_TYPE.PARAGRAPH:
            return self
        return target

    @next_paragraph_style.setter
    def next_paragraph_style(self, value) -> None:
        if self._styles is None:
            raise RuntimeError("style is detached from a Styles collection")
        if self.style_type != WD_STYLE_TYPE.PARAGRAPH:
            raise ValueError("next_paragraph_style is only valid for paragraph styles")
        if value is None:
            self.next_style_id_ref = self.id
            return
        target = self._styles.resolve(value)
        if target.style_type != WD_STYLE_TYPE.PARAGRAPH:
            raise ValueError("next paragraph style must be a paragraph style")
        self.next_style_id_ref = self.id if target.id == self.id else target.id

    @property
    def font(self):
        if self._styles is None:
            raise RuntimeError("style is detached from a Styles collection")
        return StyleFont(self)

    @property
    def paragraph_format(self):
        if self._styles is None:
            raise RuntimeError("style is detached from a Styles collection")
        return StyleParagraphFormat(self)

    def delete(self) -> None:
        """Delete this style and compact the HWPX style-id space safely.

        Hancom commonly treats shared definition IDs as dense/index-like
        tables. Deleting a middle style without remapping later IDs can make
        a structurally well-formed package fail in the editor, so this method
        updates every ``styleIDRef``/``nextStyleIDRef`` together.
        """
        if self._styles is None:
            raise RuntimeError("style is detached from a Styles collection")
        if self.id == "0":
            raise ValueError("the default style cannot be deleted")
        container = self._styles._style_container()
        before = [n for n in container.children if local_name(n.tag) == "style"]
        if self._model not in before:
            return
        fallback = self._styles.get("Normal") or self._styles.get(0)
        fallback_old = "0" if fallback is None or fallback.id == self.id else fallback.id
        remaining = [n for n in before if n is not self._model]
        remap = {node.get("id") or str(i): str(i) for i, node in enumerate(remaining)}

        def mapped(old: str | None) -> str:
            source = fallback_old if old == self.id else (old or fallback_old)
            return remap.get(source, remap.get(fallback_old, "0"))

        for section in self._styles._doc.section_models:
            for node in section.iter():
                if node.get("styleIDRef") is not None:
                    node.set("styleIDRef", mapped(node.get("styleIDRef")))
        for node in remaining:
            if node.get("nextStyleIDRef") is not None:
                node.set("nextStyleIDRef", mapped(node.get("nextStyleIDRef")))
        for old_node in remaining:
            old_id = old_node.get("id") or "0"
            old_node.set("id", remap[old_id])
        container.children[:] = [n for n in container.children if local_name(n.tag) != "style"] + remaining
        _update_count(container, "style")

    def __repr__(self) -> str:
        return f"<Style id={self.id!r} name={self.name!r} type={self.type!r}>"


class Styles:
    """Header style registry with copy-on-write mutation.

    Existing definitions are never edited or renumbered. A requested change is
    applied to a clone, deduplicated against existing definitions, and appended
    only when needed. Runs/paragraphs/cells then repoint to the returned id.
    """

    def __init__(self, document: "Document"):
        self._doc = document
        # Only definitions minted by this in-memory editing session are eligible
        # for GC. Pre-existing ids are never removed or renumbered.
        self._created_char_ids: set[str] = set()
        self._created_para_ids: set[str] = set()
        self._created_border_ids: set[str] = set()

    @property
    def _header(self) -> ElementModel:
        return self._doc.header_model

    def _style_container(self) -> ElementModel:
        return _container(self._header, "styles")

    @property
    def all(self) -> dict[str, Style]:
        return {style.id: style for style in self._style_objects()}

    def _style_objects(self) -> list[Style]:
        return [Style(node, self) for node in _children(self._style_container(), "style")]

    def __len__(self) -> int:
        return len(self._style_objects())

    def __iter__(self) -> Iterator[Style]:
        # python-docx iteration yields style objects, not style identifiers.
        return iter(self._style_objects())

    def __contains__(self, key: object) -> bool:
        try:
            self.resolve(key)  # type: ignore[arg-type]
        except (KeyError, ValueError, TypeError):
            return False
        return True

    def __getitem__(self, key: str | int) -> Style:
        return self.resolve(key)

    def default(self, style_type: WD_STYLE_TYPE | str):
        """Return the default style for the requested supported style type.

        HWPX has a clear paragraph default (style id 0 / Normal). A separate
        default-character-style contract equivalent to DOCX has not been
        verified, so CHARACTER currently returns ``None`` rather than
        inventing one.
        """
        kind = self._normalize_style_type(style_type)
        if kind == "PARA":
            return self.get(0)
        return None

    def names(self) -> list[str]:
        result: list[str] = []
        for style in self._style_objects():
            for value in (style.name, style.eng_name):
                if value and value not in result:
                    result.append(value)
        return result

    def get(self, key: str | int | Style | None, default=None):
        try:
            return self.resolve(key)
        except (KeyError, ValueError):
            return default

    def resolve(self, key: str | int | Style | None) -> Style:
        if isinstance(key, Style):
            return key
        if key is None:
            raise KeyError(key)
        styles = self._style_objects()
        raw = str(key).strip()
        if isinstance(key, int) or raw.lstrip("-").isdigit():
            wanted = str(int(raw))
            for style in styles:
                try:
                    if str(int(style.id)) == wanted:
                        return style
                except ValueError:
                    if style.id == raw:
                        return style
            raise KeyError(key)
        lowered = raw.casefold()
        matches = [
            style for style in styles
            if (style.name or "").casefold() == lowered or (style.eng_name or "").casefold() == lowered
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"ambiguous style name: {key!r}")
        raise KeyError(key)

    @staticmethod
    def _normalize_style_type(style_type: WD_STYLE_TYPE | str) -> str:
        if isinstance(style_type, WD_STYLE_TYPE):
            if style_type == WD_STYLE_TYPE.PARAGRAPH:
                return "PARA"
            if style_type == WD_STYLE_TYPE.CHARACTER:
                return "CHAR"
            raise HwpxUnsupportedError(
                f"HWPX mapping for style type {style_type.name} is not verified",
                code="style-type-unverified",
                context={"requested": style_type.name},
            )
        kind = str(style_type).strip().upper()
        aliases = {"PARAGRAPH":"PARA", "PARA":"PARA", "CHARACTER":"CHAR", "CHAR":"CHAR"}
        if kind not in aliases:
            raise HwpxValueError("style_type must be PARAGRAPH/PARA or CHARACTER/CHAR", code="style-type-invalid", context={"requested": str(style_type)})
        return aliases[kind]

    def add_style(
        self, name: str, style_type: WD_STYLE_TYPE | str = WD_STYLE_TYPE.PARAGRAPH,
        builtin: bool = False, *, clone_from: str | int | Style | None = None
    ) -> Style:
        """Create a named style, cloning an existing style's references by default.

        ``style_type`` accepts ``PARA``/``PARAGRAPH`` and ``CHAR``/``CHARACTER``.
        HWPX has no OOXML-style basedOn chain, so ``clone_from`` copies the base
        style's charPr/paraPr references instead of pretending there is one.
        """
        value = str(name).strip()
        if not value:
            raise HwpxValueError("style name must not be empty", code="style-name-empty")
        if self.get(value) is not None:
            raise HwpxValueError(f"style already exists: {value!r}", code="style-name-duplicate", context={"name": value})
        if builtin:
            raise HwpxUnsupportedError("HWPX has no verified python-docx builtin-style flag mapping", code="builtin-style-unverified")
        kind = self._normalize_style_type(style_type)
        base = self.resolve(clone_from) if clone_from is not None else self.resolve("Normal")
        container = self._style_container()
        new_id = _next_id(container, "style")
        attrs = [
            ("id", new_id), ("type", kind), ("name", value), ("engName", value),
            ("paraPrIDRef", base.para_pr_id_ref or "0"),
            ("charPrIDRef", base.char_pr_id_ref or "0"),
            ("nextStyleIDRef", new_id), ("langID", "0"), ("lockForm", "0"),
        ]
        model = ElementModel(HH + "style", attrs=attrs)
        container.children.append(model)
        _update_count(container, "style")
        return Style(model, self)

    @property
    def style_count(self) -> int:
        return len(self)

    @property
    def char_count(self) -> int:
        return len(_children(_container(self._header, "charProperties"), "charPr"))

    @property
    def paragraph_count(self) -> int:
        return len(_children(_container(self._header, "paraProperties"), "paraPr"))

    @property
    def border_fill_count(self) -> int:
        return len(_children(_container(self._header, "borderFills"), "borderFill"))

    def char_property(self, identifier: str | int | None) -> ElementModel | None:
        return _by_id(_container(self._header, "charProperties"), "charPr", identifier)

    def paragraph_property(self, identifier: str | int | None) -> ElementModel | None:
        return _by_id(_container(self._header, "paraProperties"), "paraPr", identifier)

    def border_fill(self, identifier: str | int | None) -> ElementModel | None:
        return _by_id(_container(self._header, "borderFills"), "borderFill", identifier)

    def font_face(self, char_pr_id_ref: str | int | None, lang: str = "HANGUL") -> str | None:
        cp = self.char_property(char_pr_id_ref)
        if cp is None:
            return None
        lang = lang.upper()
        attr = _FONT_LANGS.get(lang)
        if attr is None:
            raise ValueError(f"unsupported font language: {lang}")
        ref = _child(cp, "fontRef")
        if ref is None:
            return None
        font_id = ref.get(attr)
        if font_id is None:
            return None
        block = self._fontface_block(lang)
        if block is None:
            return None
        font = _by_id(block, "font", font_id)
        return None if font is None else font.get("face")

    def _fontface_block(self, lang: str) -> ElementModel | None:
        faces = _container(self._header, "fontfaces")
        return next(
            (c for c in faces.children if local_name(c.tag) == "fontface" and (c.get("lang") or "").upper() == lang),
            None,
        )

    def ensure_font(self, face: str) -> dict[str, str]:
        face = face.strip()
        if not face:
            raise ValueError("font face must not be empty")
        result: dict[str, str] = {}
        faces = _container(self._header, "fontfaces")
        for lang, ref_attr in _FONT_LANGS.items():
            block = self._fontface_block(lang)
            if block is None:
                block = ElementModel(HH + "fontface", attrs=[("lang", lang), ("fontCnt", "0")])
                faces.children.append(block)
            existing = next(
                (f for f in block.children if local_name(f.tag) == "font" and f.get("face") == face),
                None,
            )
            if existing is None:
                new_id = _next_id(block, "font")
                existing = ElementModel(
                    HH + "font",
                    attrs=[("id", new_id), ("face", face), ("type", "TTF"), ("isEmbedded", "0")],
                )
                block.children.append(existing)
                _update_count(block, "font", attr="fontCnt")
            result[ref_attr] = existing.get("id") or "0"
        _update_count(faces, "fontface")
        return result

    def tab_property(self, identifier: str | int | None) -> ElementModel | None:
        return _by_id(_container(self._header, "tabProperties"), "tabPr", identifier)

    @staticmethod
    def _normalize_tab_alignment(value) -> str:
        if isinstance(value, WD_TAB_ALIGNMENT):
            return _TAB_ALIGN_TO_HWPX[value]
        raw = str(getattr(value, "name", value)).strip().upper()
        aliases = {"LEFT":"LEFT", "CENTER":"CENTER", "RIGHT":"RIGHT", "DECIMAL":"DECIMAL"}
        if raw not in aliases:
            raise ValueError("tab alignment must be LEFT, CENTER, RIGHT, or DECIMAL")
        return aliases[raw]

    @staticmethod
    def _normalize_tab_leader(value) -> str:
        if isinstance(value, WD_TAB_LEADER):
            return _TAB_LEADER_TO_HWPX[value]
        raw = str(getattr(value, "name", value)).strip().upper()
        aliases = {
            "SPACES":"NONE", "NONE":"NONE", "DOTS":"DOT", "DOT":"DOT",
            "DASHES":"DASH", "DASH":"DASH", "LINES":"SOLID", "SOLID":"SOLID",
            "DASH_DOT":"DASH_DOT", "LONG_DASH":"LONG_DASH",
        }
        if raw not in aliases:
            raise ValueError("unsupported tab leader")
        return aliases[raw]

    def tab_stops_for(self, identifier: str | int | None) -> list[tuple[int, str, str]]:
        tab_pr = self.tab_property(identifier)
        if tab_pr is None:
            return []
        direct = [c for c in tab_pr.children if local_name(c.tag) == "tabItem"]
        if direct:
            return [(int(c.get("pos") or 0), c.get("type") or "LEFT", c.get("leader") or "NONE") for c in direct]
        out: list[tuple[int, str, str]] = []
        for switch in tab_pr.children:
            if local_name(switch.tag) != "switch":
                continue
            case = next((c for c in switch.children if local_name(c.tag) == "case"), None)
            if case is None:
                continue
            item = next((c for c in case.children if local_name(c.tag) == "tabItem"), None)
            if item is not None:
                out.append((int(item.get("pos") or 0), item.get("type") or "LEFT", item.get("leader") or "NONE"))
        return out

    def ensure_tab_definition(
        self, tab_stops: Iterable[dict[str, object]] | None = None, *,
        auto_tab_left: bool = False, auto_tab_right: bool = False,
    ) -> str:
        container = _container(self._header, "tabProperties")
        normalized: list[tuple[int, str, str]] = []
        for spec in tab_stops or []:
            if "pos" not in spec:
                raise ValueError("tab stop requires pos")
            pos = int(spec["pos"])
            if pos < 0:
                raise ValueError("HWPX tab stop position must be non-negative")
            kind = self._normalize_tab_alignment(spec.get("type", "LEFT"))
            leader = self._normalize_tab_leader(spec.get("leader", "NONE"))
            normalized.append((pos, kind, leader))
        normalized.sort(key=lambda item: item[0])
        for existing in _children(container, "tabPr"):
            if (existing.get("autoTabLeft", "0") == ("1" if auto_tab_left else "0") and
                existing.get("autoTabRight", "0") == ("1" if auto_tab_right else "0") and
                self.tab_stops_for(existing.get("id")) == normalized):
                return existing.get("id") or "0"
        new_id = _next_id(container, "tabPr")
        tab_pr = ElementModel(HH + "tabPr", attrs=[
            ("id", new_id), ("autoTabLeft", "1" if auto_tab_left else "0"),
            ("autoTabRight", "1" if auto_tab_right else "0"),
        ])
        for pos, kind, leader in normalized:
            switch = ElementModel(HP + "switch")
            case = ElementModel(HP + "case", attrs=[(HP + "required-namespace", _HWPUNITCHAR_NS)])
            case.children.append(ElementModel(HH + "tabItem", attrs=[
                ("pos", str(pos)), ("type", kind), ("leader", leader), ("unit", "HWPUNIT")
            ]))
            default = ElementModel(HP + "default")
            default.children.append(ElementModel(HH + "tabItem", attrs=[
                ("pos", str(pos * 2)), ("type", kind), ("leader", leader)
            ]))
            switch.children.extend([case, default])
            tab_pr.children.append(switch)
        container.children.append(tab_pr)
        _update_count(container, "tabPr")
        return new_id

    def rebase_char_property(
        self,
        direct_char_pr_id: str | int | None,
        old_base_char_pr_id: str | int | None,
        new_base_char_pr_id: str | int | None,
    ) -> str:
        """Rebase flat HWPX run formatting onto a new paragraph-style base.

        HWPX materializes character formatting as complete ``charPr`` records,
        while python-docx conceptually layers direct run formatting over a
        paragraph style. When a paragraph style changes we perform a generic
        three-way merge: differences between *old base* and *direct* are
        applied to *new base*. Unknown charPr attributes/children participate
        too, so the operation does not silently discard extension formatting.
        """
        container = _container(self._header, "charProperties")
        direct = _by_id(container, "charPr", direct_char_pr_id)
        old_base = _by_id(container, "charPr", old_base_char_pr_id)
        new_base = _by_id(container, "charPr", new_base_char_pr_id)
        if new_base is None:
            return str(direct_char_pr_id or "0")
        if direct is None or old_base is None:
            return new_base.get("id") or "0"
        if _signature(direct, ignore_id=True) == _signature(old_base, ignore_id=True):
            return new_base.get("id") or "0"

        candidate = _clone(new_base)
        candidate.attrs = [(k, v) for k, v in candidate.attrs if k != "id"]
        old_attrs = {k: v for k, v in old_base.attrs if k != "id"}
        direct_attrs = {k: v for k, v in direct.attrs if k != "id"}
        for key in sorted(set(old_attrs) | set(direct_attrs)):
            old_value = old_attrs.get(key)
            direct_value = direct_attrs.get(key)
            if old_value == direct_value:
                continue
            candidate.attrs[:] = [(k, v) for k, v in candidate.attrs if k != key]
            if direct_value is not None:
                candidate.attrs.append((key, direct_value))

        def grouped(node: ElementModel) -> dict[str, list[ElementModel]]:
            result: dict[str, list[ElementModel]] = {}
            for child in node.children:
                result.setdefault(local_name(child.tag), []).append(child)
            return result

        old_groups = grouped(old_base)
        direct_groups = grouped(direct)
        for lname in sorted(set(old_groups) | set(direct_groups)):
            old_sig = tuple(_signature(x) for x in old_groups.get(lname, []))
            direct_sig = tuple(_signature(x) for x in direct_groups.get(lname, []))
            if old_sig == direct_sig:
                continue
            positions = [i for i, child in enumerate(candidate.children) if local_name(child.tag) == lname]
            insert_at = positions[0] if positions else len(candidate.children)
            candidate.children[:] = [child for child in candidate.children if local_name(child.tag) != lname]
            replacements = [_clone(child) for child in direct_groups.get(lname, [])]
            candidate.children[insert_at:insert_at] = replacements

        wanted = _signature(candidate, ignore_id=True)
        for existing in container.children:
            if local_name(existing.tag) == "charPr" and _signature(existing, ignore_id=True) == wanted:
                return existing.get("id") or "0"
        new_id = _next_id(container, "charPr")
        candidate.set("id", new_id)
        container.children.append(candidate)
        _update_count(container, "charPr")
        self._created_char_ids.add(new_id)
        return new_id

    def ensure_run(
        self,
        *,
        base_char_pr_id: str | int | None = None,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
        underline_color: str | None = None,
        strike: bool | None = None,
        color: str | None = None,
        font: str | None = None,
        size: int | float | Length | None = None,
        highlight: str | None = None,
        subscript: bool | None = None,
        superscript: bool | None = None,
        shadow: bool | None = None,
        outline: bool | None = None,
        emboss: bool | None = None,
        engrave: bool | None = None,
    ) -> str:
        container = _container(self._header, "charProperties")
        base = _by_id(container, "charPr", base_char_pr_id)
        if base is None:
            base = next((c for c in container.children if local_name(c.tag) == "charPr"), None)
        if base is None:
            raise ValueError("header has no charPr definition")
        candidate = _clone(base)
        candidate.attrs = [(k, v) for k, v in candidate.attrs if k != "id"]

        if color is not None:
            candidate.set("textColor", _norm_color(color))
        if size is not None:
            candidate.set("height", str(_font_size_height(size)))
        if font is not None:
            refs = self.ensure_font(font)
            font_ref = _ensure_char_child(candidate, "fontRef")
            for attr, identifier in refs.items():
                font_ref.set(attr, identifier)

        for name, value in (("bold", bold), ("italic", italic)):
            if value is True:
                _ensure_char_child(candidate, name)
            elif value is False:
                _remove_children(candidate, name)

        if underline is not None or underline_color is not None:
            underline_el = _ensure_char_child(
                candidate, "underline", {"type": "NONE", "shape": "SOLID", "color": "#000000"}
            )
            if underline is not None:
                underline_el.set("type", "BOTTOM" if underline else "NONE")
            if underline_el.get("shape") is None:
                underline_el.set("shape", "SOLID")
            if underline_color is not None:
                underline_el.set("color", _norm_color(underline_color))
            elif underline_el.get("color") is None:
                underline_el.set("color", "#000000")

        if strike is not None:
            strike_el = _ensure_char_child(candidate, "strikeout", {"shape": "NONE", "color": "#000000"})
            strike_el.set("shape", "SOLID" if strike else "NONE")
            if strike_el.get("color") is None:
                strike_el.set("color", "#000000")

        if highlight is not None:
            candidate.set("shadeColor", "none" if str(highlight).lower() == "none" else _norm_color(highlight))
        if subscript is not None:
            if subscript:
                _remove_children(candidate, "supscript"); _ensure_char_child(candidate, "subscript")
            else:
                _remove_children(candidate, "subscript")
        if superscript is not None:
            if superscript:
                _remove_children(candidate, "subscript"); _ensure_char_child(candidate, "supscript")
            else:
                _remove_children(candidate, "supscript")
        if shadow is not None:
            sh = _ensure_char_child(candidate, "shadow", {"type":"NONE","color":"#C0C0C0","offsetX":"10","offsetY":"10"})
            sh.set("type", "DROP" if shadow else "NONE")
        if outline is not None:
            ol = _ensure_char_child(candidate, "outline", {"type":"NONE"})
            ol.set("type", "SOLID" if outline else "NONE")
        for name, value in (("emboss", emboss), ("engrave", engrave)):
            if value is True:
                _ensure_char_child(candidate, name)
            elif value is False:
                _remove_children(candidate, name)

        wanted = _signature(candidate, ignore_id=True)
        for existing in container.children:
            if local_name(existing.tag) == "charPr" and _signature(existing, ignore_id=True) == wanted:
                return existing.get("id") or "0"

        new_id = _next_id(container, "charPr")
        candidate.set("id", new_id)
        container.children.append(candidate)
        _update_count(container, "charPr")
        self._created_char_ids.add(new_id)
        return new_id

    def ensure_paragraph(
        self,
        *,
        base_para_pr_id: str | int | None = None,
        alignment: str | None = None,
        line_spacing_percent: int | float | None = None,
        first_line_indent: int | Length | None = None,
        left_indent: int | Length | None = None,
        right_indent: int | Length | None = None,
        space_before: int | Length | None = None,
        space_after: int | Length | None = None,
        keep_with_next: bool | None = None,
        keep_lines: bool | None = None,
        page_break_before: bool | None = None,
        tab_pr_id_ref: str | int | None = None,
    ) -> str:
        container = _container(self._header, "paraProperties")
        base = _by_id(container, "paraPr", base_para_pr_id)
        if base is None:
            base = next((c for c in container.children if local_name(c.tag) == "paraPr"), None)
        if base is None:
            raise ValueError("header has no paraPr definition")
        candidate = _clone(base)
        candidate.attrs = [(k, v) for k, v in candidate.attrs if k != "id"]

        if tab_pr_id_ref is not None:
            candidate.set("tabPrIDRef", str(tab_pr_id_ref))

        if alignment is not None:
            aliases = {
                "LEFT": "LEFT", "START": "LEFT", "CENTER": "CENTER", "CENTRE": "CENTER",
                "RIGHT": "RIGHT", "END": "RIGHT", "JUSTIFY": "JUSTIFY",
                "DISTRIBUTE": "DISTRIBUTE", "DISTRIBUTE_SPACE": "DISTRIBUTE_SPACE",
            }
            normalized = aliases.get(str(alignment).upper())
            if normalized is None:
                raise ValueError(f"unsupported paragraph alignment: {alignment}")
            align = _child(candidate, "align")
            if align is None:
                align = ElementModel(HH + "align", attrs=[("horizontal", normalized), ("vertical", "BASELINE")])
                candidate.children.insert(0, align)
            else:
                align.set("horizontal", normalized)
                if align.get("vertical") is None:
                    align.set("vertical", "BASELINE")

        if line_spacing_percent is not None:
            nodes = _desc(candidate, "lineSpacing")
            if not nodes:
                node = ElementModel(HH + "lineSpacing", attrs=[("type", "PERCENT"), ("value", str(round(float(line_spacing_percent)))), ("unit", "PERCENT")])
                candidate.children.append(node)
                nodes = [node]
            for node in nodes:
                node.set("type", "PERCENT")
                node.set("value", str(round(float(line_spacing_percent))))
                if node.get("unit") is None:
                    node.set("unit", "PERCENT")

        margin_changes = {
            "intent": first_line_indent,
            "left": left_indent,
            "right": right_indent,
            "prev": space_before,
            "next": space_after,
        }
        if any(v is not None for v in margin_changes.values()):
            self._apply_margins(candidate, margin_changes)

        if any(v is not None for v in (keep_with_next, keep_lines, page_break_before)):
            br = _child(candidate, "breakSetting")
            if br is None:
                br = ElementModel(HH + "breakSetting")
                # after heading if possible
                idx = next((i + 1 for i, c in enumerate(candidate.children) if local_name(c.tag) == "heading"), 0)
                candidate.children.insert(idx, br)
            for attr, value in (
                ("keepWithNext", keep_with_next), ("keepLines", keep_lines), ("pageBreakBefore", page_break_before)
            ):
                if value is not None:
                    br.set(attr, "1" if value else "0")

        wanted = _signature(candidate, ignore_id=True)
        for existing in container.children:
            if local_name(existing.tag) == "paraPr" and _signature(existing, ignore_id=True) == wanted:
                return existing.get("id") or "0"
        new_id = _next_id(container, "paraPr")
        candidate.set("id", new_id)
        container.children.append(candidate)
        _update_count(container, "paraPr")
        self._created_para_ids.add(new_id)
        return new_id

    def _apply_margins(self, para_pr: ElementModel, changes: dict[str, int | Length | None]) -> None:
        margins: list[tuple[ElementModel, int]] = []

        def walk(node: ElementModel, multiplier: int = 1) -> None:
            here = multiplier * (2 if local_name(node.tag) == "default" else 1)
            if local_name(node.tag) == "margin":
                margins.append((node, here))
                return
            for child in node.children:
                walk(child, here)

        walk(para_pr)
        if not margins:
            margin = ElementModel(HH + "margin")
            para_pr.children.append(margin)
            margins.append((margin, 1))
        for margin, multiplier in margins:
            for name, value in changes.items():
                if value is None:
                    continue
                child = _child(margin, name)
                if child is None:
                    child = ElementModel(HC + name)
                    margin.children.append(child)
                child.set("value", str(int(value) * multiplier))
                child.set("unit", "HWPUNIT")
                child.text = None

    def _ensure_ref_collection(self, name: str) -> ElementModel:
        ref_list = _first_desc(self._header, "refList")
        if ref_list is None:
            ref_list = ElementModel(HH + "refList")
            self._header.children.append(ref_list)
        found = next((c for c in ref_list.children if local_name(c.tag) == name), None)
        if found is None:
            found = ElementModel(HH + name, attrs=[("itemCnt", "0")])
            ref_list.children.append(found)
        return found

    @staticmethod
    def _para_head_attrs(level: int) -> list[tuple[str, str]]:
        return [
            ("start", "1"), ("level", str(level)), ("align", "LEFT"),
            ("useInstWidth", "1"), ("autoIndent", "1"), ("widthAdjust", "0"),
            ("textOffsetType", "PERCENT"), ("textOffset", "50"),
            ("numFormat", "DIGIT"), ("charPrIDRef", "4294967295"),
            ("checkable", "0"),
        ]

    @staticmethod
    def _next_ref_id(container: ElementModel, child_name: str) -> str:
        numeric: list[int] = []
        used: set[str] = set()
        for node in container.children:
            if local_name(node.tag) != child_name:
                continue
            raw = node.get("id") or ""
            used.add(raw)
            try:
                numeric.append(int(raw))
            except ValueError:
                pass
        value = max(numeric, default=0) + 1
        while str(value) in used:
            value += 1
        return str(value)

    def _ensure_para_heading(self, heading_type: str, id_ref: str, level: int) -> str:
        container = _container(self._header, "paraProperties")
        for para_pr in container.children:
            if local_name(para_pr.tag) != "paraPr":
                continue
            heading = _child(para_pr, "heading")
            if heading is not None and (
                heading.get("type") == heading_type
                and heading.get("idRef") == str(id_ref)
                and heading.get("level") == str(level)
            ):
                return para_pr.get("id") or "0"
        base = next((c for c in container.children if local_name(c.tag) == "paraPr"), None)
        if base is None:
            raise ValueError("header has no paraPr definition")
        candidate = _clone(base)
        candidate.attrs = [(k, v) for k, v in candidate.attrs if k != "id"]
        heading = _child(candidate, "heading")
        if heading is None:
            heading = ElementModel(HH + "heading")
            idx = next((i + 1 for i, c in enumerate(candidate.children) if local_name(c.tag) == "align"), 0)
            candidate.children.insert(idx, heading)
        heading.set("type", heading_type)
        heading.set("idRef", str(id_ref))
        heading.set("level", str(level))
        wanted = _signature(candidate, ignore_id=True)
        for existing in container.children:
            if local_name(existing.tag) == "paraPr" and _signature(existing, ignore_id=True) == wanted:
                return existing.get("id") or "0"
        new_id = _next_id(container, "paraPr")
        candidate.set("id", new_id)
        container.children.append(candidate)
        _update_count(container, "paraPr")
        self._created_para_ids.add(new_id)
        return new_id

    def ensure_numbering(
        self,
        *,
        kind: str,
        levels: list[dict[str, str]] | None = None,
        restart: bool = False,
    ) -> list[str]:
        """Ensure bullet/number/outline definitions and return paraPr ids by level."""
        specs = list(levels or [{}]) or [{}]
        normalized = str(kind).strip().lower()
        if normalized == "bullet":
            defaults = ("-", "○", "□", "•")
            bullets = self._ensure_ref_collection("bullets")
            refs: list[str] = []
            for index, spec in enumerate(specs):
                char = str(spec.get("char") or defaults[index % len(defaults)])
                bullet = next(
                    (b for b in bullets.children if local_name(b.tag) == "bullet" and b.get("char") == char),
                    None,
                )
                if bullet is None:
                    bullet_id = self._next_ref_id(bullets, "bullet")
                    bullet = ElementModel(HH + "bullet", attrs=[("id", bullet_id), ("char", char), ("useImage", "0")])
                    attrs = dict(self._para_head_attrs(0))
                    attrs.pop("start", None)
                    attrs["useInstWidth"] = "0"
                    bullet.children.append(ElementModel(HH + "paraHead", attrs=list(attrs.items())))
                    bullets.children.append(bullet)
                    _update_count(bullets, "bullet")
                refs.append(self._ensure_para_heading("BULLET", bullet.get("id") or "1", index))
            return refs

        if normalized not in {"number", "numbered", "numbering", "outline"}:
            raise ValueError("kind must be 'bullet', 'number', or 'outline'")
        numberings = self._ensure_ref_collection("numberings")
        numbering_id = self._next_ref_id(numberings, "numbering")
        numbering = ElementModel(HH + "numbering", attrs=[
            ("id", numbering_id), ("start", str(specs[0].get("start") or "1")),
        ])
        for index, spec in enumerate(specs):
            level = index + 1
            attrs = dict(self._para_head_attrs(level))
            if spec.get("format") or spec.get("numFormat"):
                attrs["numFormat"] = str(spec.get("numFormat") or spec.get("format")).upper()
            if spec.get("start") is not None:
                attrs["start"] = str(spec["start"])
            head = ElementModel(HH + "paraHead", attrs=list(attrs.items()))
            head.text = str(spec.get("text") or ".".join(f"^{part}" for part in range(1, level + 1)) + ".")
            numbering.children.append(head)
        # Reuse an identical numbering definition for continuation.  A restart
        # deliberately mints a distinct numbering id even when the visual
        # definition is identical, which is how HWPX starts a fresh sequence.
        wanted = _signature(numbering, ignore_id=True)
        existing_id = None
        if not restart:
            for existing in numberings.children:
                if local_name(existing.tag) == "numbering" and _signature(existing, ignore_id=True) == wanted:
                    existing_id = existing.get("id")
                    break
        if existing_id is None:
            numberings.children.append(numbering)
            _update_count(numberings, "numbering")
            existing_id = numbering_id
        heading_type = "OUTLINE" if normalized == "outline" else "NUMBER"
        return [self._ensure_para_heading(heading_type, existing_id or numbering_id, i) for i in range(len(specs))]

    def ensure_border_fill(
        self,
        *,
        base_border_fill_id: str | int | None = None,
        color: str | None = None,
        width: str | None = None,
        border_type: str | None = None,
        fill_color: str | None = None,
        sides: Iterable[str] | None = None,
    ) -> str:
        container = _container(self._header, "borderFills")
        base = _by_id(container, "borderFill", base_border_fill_id)
        if base is None:
            base = next((c for c in container.children if local_name(c.tag) == "borderFill"), None)
        if base is None:
            raise ValueError("header has no borderFill definition")
        candidate = _clone(base)
        candidate.attrs = [(k, v) for k, v in candidate.attrs if k != "id"]

        active = set(_BORDER_SIDES if sides is None else sides)
        bad = active - set(_BORDER_SIDES)
        if bad:
            raise ValueError(f"unsupported border sides: {sorted(bad)}")
        for side in _BORDER_SIDES:
            if side not in active:
                continue
            line = _child(candidate, side)
            if line is None:
                line = ElementModel(HH + side, attrs=[("type", "SOLID"), ("width", "0.12 mm"), ("color", "#000000")])
                candidate.children.append(line)
            if color is not None:
                line.set("color", _norm_color(color))
            if width is not None:
                line.set("width", str(width))
            if border_type is not None:
                line.set("type", str(border_type).upper())

        if fill_color is not None:
            brush = _child(candidate, "fillBrush")
            if brush is None:
                brush = ElementModel(HC + "fillBrush")
                candidate.children.append(brush)
            win = _child(brush, "winBrush")
            if win is None:
                win = ElementModel(HC + "winBrush", attrs=[("hatchColor", "#000000"), ("alpha", "0")])
                brush.children.append(win)
            win.set("faceColor", _norm_color(fill_color))
            if win.get("hatchColor") is None:
                win.set("hatchColor", "#000000")
            if win.get("alpha") is None:
                win.set("alpha", "0")

        wanted = _signature(candidate, ignore_id=True)
        for existing in container.children:
            if local_name(existing.tag) == "borderFill" and _signature(existing, ignore_id=True) == wanted:
                return existing.get("id") or "0"
        new_id = _next_id(container, "borderFill")
        candidate.set("id", new_id)
        container.children.append(candidate)
        _update_count(container, "borderFill")
        self._created_border_ids.add(new_id)
        return new_id

    def prune_orphans(self) -> dict[str, int]:
        """Keep session-created shared definitions to preserve dense HWPX IDs.

        Hancom-produced files use dense/index-like ID spaces for charPr and
        paraPr (0..itemCnt-1) and borderFill (1..itemCnt).  Removing an
        intermediate copy-on-write definition leaves holes while later
        references retain their larger IDs; Hancom can reject such a file.

        For compatibility this method is intentionally a no-op.  Dedupe still
        prevents identical definitions from being added repeatedly, and no
        existing IDs are renumbered.
        """
        return {"charPr": 0, "paraPr": 0, "borderFill": 0}



class Font:
    def __init__(self, run: "Run"):
        self._run = run

    @property
    def _styles(self) -> Styles:
        if self._run.document is None:
            raise RuntimeError("run is not attached to a document")
        return self._run.document.styles

    @property
    def name(self) -> str | None:
        return self._styles.font_face(self._run.char_pr_id_ref, "HANGUL")

    @name.setter
    def name(self, value: str) -> None:
        self._run.char_pr_id_ref = self._styles.ensure_run(base_char_pr_id=self._run.char_pr_id_ref, font=value)

    @property
    def size(self) -> Length | None:
        cp = self._styles.char_property(self._run.char_pr_id_ref)
        if cp is None or cp.get("height") is None:
            return None
        return HwpUnit(int(cp.get("height") or "0"))

    @size.setter
    def size(self, value: int | float | Length) -> None:
        self._run.char_pr_id_ref = self._styles.ensure_run(base_char_pr_id=self._run.char_pr_id_ref, size=value)

    @property
    def color(self) -> str | None:
        cp = self._styles.char_property(self._run.char_pr_id_ref)
        return None if cp is None else cp.get("textColor")

    @color.setter
    def color(self, value: str) -> None:
        self._run.char_pr_id_ref = self._styles.ensure_run(base_char_pr_id=self._run.char_pr_id_ref, color=value)

    def _flag(self, name: str) -> bool:
        cp = self._styles.char_property(self._run.char_pr_id_ref)
        return bool(cp and _child(cp, name) is not None)

    @property
    def bold(self) -> bool:
        return self._flag("bold")

    @bold.setter
    def bold(self, value: bool) -> None:
        self._run.char_pr_id_ref = self._styles.ensure_run(base_char_pr_id=self._run.char_pr_id_ref, bold=bool(value))

    @property
    def italic(self) -> bool:
        return self._flag("italic")

    @italic.setter
    def italic(self, value: bool) -> None:
        self._run.char_pr_id_ref = self._styles.ensure_run(base_char_pr_id=self._run.char_pr_id_ref, italic=bool(value))

    @property
    def underline(self) -> bool:
        cp = self._styles.char_property(self._run.char_pr_id_ref)
        el = None if cp is None else _child(cp, "underline")
        return bool(el and (el.get("type") or "NONE").upper() != "NONE")

    @underline.setter
    def underline(self, value: bool) -> None:
        self._run.char_pr_id_ref = self._styles.ensure_run(base_char_pr_id=self._run.char_pr_id_ref, underline=bool(value))

    @property
    def strike(self) -> bool:
        cp = self._styles.char_property(self._run.char_pr_id_ref)
        el = None if cp is None else _child(cp, "strikeout")
        return bool(el and (el.get("shape") or "NONE").upper() != "NONE")

    @strike.setter
    def strike(self, value: bool) -> None:
        self._run.char_pr_id_ref = self._styles.ensure_run(base_char_pr_id=self._run.char_pr_id_ref, strike=bool(value))

    @property
    def subscript(self) -> bool:
        return self._flag("subscript")
    @subscript.setter
    def subscript(self, value: bool) -> None:
        self._run.char_pr_id_ref = self._styles.ensure_run(base_char_pr_id=self._run.char_pr_id_ref, subscript=bool(value))

    @property
    def superscript(self) -> bool:
        return self._flag("supscript")
    @superscript.setter
    def superscript(self, value: bool) -> None:
        self._run.char_pr_id_ref = self._styles.ensure_run(base_char_pr_id=self._run.char_pr_id_ref, superscript=bool(value))

    @property
    def shadow(self) -> bool:
        cp=self._styles.char_property(self._run.char_pr_id_ref); el=None if cp is None else _child(cp,"shadow")
        return bool(el and (el.get("type") or "NONE").upper() != "NONE")
    @shadow.setter
    def shadow(self, value: bool) -> None:
        self._run.char_pr_id_ref = self._styles.ensure_run(base_char_pr_id=self._run.char_pr_id_ref, shadow=bool(value))

    @property
    def outline(self) -> bool:
        cp=self._styles.char_property(self._run.char_pr_id_ref); el=None if cp is None else _child(cp,"outline")
        return bool(el and (el.get("type") or "NONE").upper() != "NONE")
    @outline.setter
    def outline(self, value: bool) -> None:
        self._run.char_pr_id_ref = self._styles.ensure_run(base_char_pr_id=self._run.char_pr_id_ref, outline=bool(value))

    emboss = property(lambda s: s._flag("emboss"), lambda s,v: setattr(s._run, "char_pr_id_ref", s._styles.ensure_run(base_char_pr_id=s._run.char_pr_id_ref, emboss=bool(v))))
    engrave = property(lambda s: s._flag("engrave"), lambda s,v: setattr(s._run, "char_pr_id_ref", s._styles.ensure_run(base_char_pr_id=s._run.char_pr_id_ref, engrave=bool(v))))

    @property
    def highlight_color(self) -> str | None:
        cp=self._styles.char_property(self._run.char_pr_id_ref)
        return None if cp is None else cp.get("shadeColor")
    @highlight_color.setter
    def highlight_color(self, value: str) -> None:
        self._run.char_pr_id_ref = self._styles.ensure_run(base_char_pr_id=self._run.char_pr_id_ref, highlight=value)


class StyleFont:
    def __init__(self, style: Style):
        self._style = style
        self._styles = style._styles

    def _cp(self):
        return self._styles.char_property(self._style.char_pr_id_ref)

    def _derive(self, **kwargs):
        self._style.char_pr_id_ref = self._styles.ensure_run(base_char_pr_id=self._style.char_pr_id_ref, **kwargs)

    @property
    def name(self):
        return self._styles.font_face(self._style.char_pr_id_ref)
    @name.setter
    def name(self, v): self._derive(font=v)
    @property
    def size(self):
        cp=self._cp(); return None if cp is None or cp.get("height") is None else HwpUnit(int(cp.get("height") or 0))
    @size.setter
    def size(self, v): self._derive(size=v)
    @property
    def color(self):
        cp=self._cp(); return None if cp is None else cp.get("textColor")
    @color.setter
    def color(self, v): self._derive(color=v)
    def _flag(self, name):
        cp=self._cp(); return False if cp is None else _child(cp,name) is not None
    bold=property(lambda s:s._flag("bold"), lambda s,v:s._derive(bold=bool(v)))
    italic=property(lambda s:s._flag("italic"), lambda s,v:s._derive(italic=bool(v)))
    subscript=property(lambda s:s._flag("subscript"), lambda s,v:s._derive(subscript=bool(v)))
    superscript=property(lambda s:s._flag("supscript"), lambda s,v:s._derive(superscript=bool(v)))
    emboss=property(lambda s:s._flag("emboss"), lambda s,v:s._derive(emboss=bool(v)))
    engrave=property(lambda s:s._flag("engrave"), lambda s,v:s._derive(engrave=bool(v)))
    @property
    def highlight_color(self):
        cp=self._cp(); return None if cp is None else cp.get("shadeColor")
    @highlight_color.setter
    def highlight_color(self,v): self._derive(highlight=v)


class StyleParagraphFormat:
    def __init__(self, style: Style):
        self._style=style; self._styles=style._styles
    def _prop(self): return self._styles.paragraph_property(self._style.para_pr_id_ref)
    def _derive(self, **kwargs): self._style.para_pr_id_ref=self._styles.ensure_paragraph(base_para_pr_id=self._style.para_pr_id_ref, **kwargs)
    @property
    def alignment(self):
        pp=self._prop(); el=None if pp is None else _child(pp,"align"); return None if el is None else el.get("horizontal")
    @alignment.setter
    def alignment(self,v): self._derive(alignment=v)
    @property
    def space_before(self):
        pp=self._prop(); m=None if pp is None else _first_desc(pp,"margin"); return None if m is None else HwpUnit(_node_numeric_value(_child(m,"prev")) or 0)
    @space_before.setter
    def space_before(self,v): self._derive(space_before=v)
    @property
    def space_after(self):
        pp=self._prop(); m=None if pp is None else _first_desc(pp,"margin"); return None if m is None else HwpUnit(_node_numeric_value(_child(m,"next")) or 0)
    @space_after.setter
    def space_after(self,v): self._derive(space_after=v)


class TabStop:
    def __init__(self, owner: "TabStops", index: int):
        self._owner = owner
        self._index = index

    def _spec(self) -> dict[str, object]:
        return dict(self._owner._specs()[self._index])

    @property
    def position(self) -> Length:
        return HwpUnit(int(self._spec()["pos"]))

    @position.setter
    def position(self, value: int | Length) -> None:
        spec = self._spec(); spec["pos"] = int(value); self._owner._replace(self._index, spec)

    @property
    def alignment(self) -> WD_TAB_ALIGNMENT:
        return _TAB_ALIGN_FROM_HWPX.get(str(self._spec()["type"]), WD_TAB_ALIGNMENT.LEFT)

    @alignment.setter
    def alignment(self, value) -> None:
        spec = self._spec(); spec["type"] = self._owner._styles._normalize_tab_alignment(value); self._owner._replace(self._index, spec)

    @property
    def leader(self) -> WD_TAB_LEADER:
        return _TAB_LEADER_FROM_HWPX.get(str(self._spec()["leader"]), WD_TAB_LEADER.SPACES)

    @leader.setter
    def leader(self, value) -> None:
        spec = self._spec(); spec["leader"] = self._owner._styles._normalize_tab_leader(value); self._owner._replace(self._index, spec)


class TabStops:
    def __init__(self, paragraph: "Paragraph"):
        self._p = paragraph

    @property
    def _styles(self) -> Styles:
        if self._p.document is None:
            raise RuntimeError("paragraph is not attached to a document")
        return self._p.document.styles

    def _specs(self) -> list[dict[str, object]]:
        pp = self._styles.paragraph_property(self._p.para_pr_id_ref)
        if pp is None:
            return []
        ref = pp.get("tabPrIDRef") or "0"
        return [{"pos": pos, "type": kind, "leader": leader} for pos, kind, leader in self._styles.tab_stops_for(ref)]

    def _apply(self, specs: list[dict[str, object]]) -> None:
        tab_id = self._styles.ensure_tab_definition(specs)
        self._p.para_pr_id_ref = self._styles.ensure_paragraph(
            base_para_pr_id=self._p.para_pr_id_ref, tab_pr_id_ref=tab_id
        )

    def _replace(self, index: int, spec: dict[str, object]) -> None:
        specs = self._specs()
        if not -len(specs) <= index < len(specs):
            raise IndexError("tab index out of range")
        specs[index] = spec
        specs.sort(key=lambda item: int(item["pos"]))
        self._apply(specs)

    def __len__(self) -> int:
        return len(self._specs())

    def __iter__(self):
        for i in range(len(self)):
            yield TabStop(self, i)

    def __getitem__(self, index: int) -> TabStop:
        specs = self._specs()
        if not specs:
            raise IndexError("TabStops object is empty")
        _ = specs[index]
        return TabStop(self, index)

    def __delitem__(self, index: int) -> None:
        specs = self._specs()
        try:
            del specs[index]
        except IndexError:
            raise IndexError("tab index out of range") from None
        self._apply(specs)

    def add_tab_stop(self, position: int | Length, alignment=WD_TAB_ALIGNMENT.LEFT, leader=WD_TAB_LEADER.SPACES) -> TabStop:
        pos = int(position)
        if pos < 0:
            raise ValueError("HWPX tab stop position must be non-negative")
        kind = self._styles._normalize_tab_alignment(alignment)
        lead = self._styles._normalize_tab_leader(leader)
        specs = self._specs()
        # Replace a stop at the same position, matching python-docx's effective behavior.
        specs = [s for s in specs if int(s["pos"]) != pos]
        specs.append({"pos": pos, "type": kind, "leader": lead})
        specs.sort(key=lambda item: int(item["pos"]))
        self._apply(specs)
        index = next(i for i, spec in enumerate(self._specs()) if int(spec["pos"]) == pos)
        return TabStop(self, index)

    def clear_all(self) -> None:
        self._apply([])


class ParagraphFormat:
    def __init__(self, paragraph: "Paragraph"):
        self._p = paragraph

    @property
    def _styles(self) -> Styles:
        if self._p.document is None:
            raise RuntimeError("paragraph is not attached to a document")
        return self._p.document.styles

    def _prop(self) -> ElementModel | None:
        return self._styles.paragraph_property(self._p.para_pr_id_ref)

    def _derive(self, **kwargs) -> None:
        self._p.para_pr_id_ref = self._styles.ensure_paragraph(base_para_pr_id=self._p.para_pr_id_ref, **kwargs)

    @property
    def alignment(self) -> str | None:
        pp = self._prop()
        el = None if pp is None else _child(pp, "align")
        return None if el is None else el.get("horizontal")

    @alignment.setter
    def alignment(self, value: str) -> None:
        self._derive(alignment=value)

    @property
    def line_spacing_percent(self) -> int | None:
        pp = self._prop()
        node = None if pp is None else _first_desc(pp, "lineSpacing")
        if node is None or node.get("value") is None:
            return None
        return int(node.get("value") or "0")

    @line_spacing_percent.setter
    def line_spacing_percent(self, value: int | float) -> None:
        self._derive(line_spacing_percent=value)

    def _margin(self, name: str) -> Length | None:
        pp = self._prop()
        if pp is None:
            return None
        # Prefer the modern hp:case branch, then a direct/default margin.
        case = next((n for n in pp.iter() if local_name(n.tag) == "case"), None)
        scopes = [case, pp] if case is not None else [pp]
        for scope in scopes:
            if scope is None:
                continue
            margin = _first_desc(scope, "margin")
            if margin is None:
                continue
            value = _node_numeric_value(_child(margin, name))
            if value is not None:
                return HwpUnit(value)
        return None

    @property
    def first_line_indent(self) -> Length | None:
        return self._margin("intent")

    @first_line_indent.setter
    def first_line_indent(self, value: int | Length) -> None:
        self._derive(first_line_indent=value)

    @property
    def left_indent(self) -> Length | None:
        return self._margin("left")

    @left_indent.setter
    def left_indent(self, value: int | Length) -> None:
        self._derive(left_indent=value)

    @property
    def right_indent(self) -> Length | None:
        return self._margin("right")

    @right_indent.setter
    def right_indent(self, value: int | Length) -> None:
        self._derive(right_indent=value)

    @property
    def space_before(self) -> Length | None:
        return self._margin("prev")

    @space_before.setter
    def space_before(self, value: int | Length) -> None:
        self._derive(space_before=value)

    @property
    def space_after(self) -> Length | None:
        return self._margin("next")

    @space_after.setter
    def space_after(self, value: int | Length) -> None:
        self._derive(space_after=value)

    def _break_flag(self, attr: str) -> bool | None:
        pp = self._prop()
        br = None if pp is None else _child(pp, "breakSetting")
        if br is None or br.get(attr) is None:
            return None
        return br.get(attr) == "1"

    @property
    def keep_with_next(self) -> bool | None:
        return self._break_flag("keepWithNext")

    @keep_with_next.setter
    def keep_with_next(self, value: bool) -> None:
        self._derive(keep_with_next=value)

    @property
    def keep_lines(self) -> bool | None:
        return self._break_flag("keepLines")

    @keep_lines.setter
    def keep_lines(self, value: bool) -> None:
        self._derive(keep_lines=value)

    @property
    def page_break_before(self) -> bool | None:
        return self._break_flag("pageBreakBefore")

    @page_break_before.setter
    def page_break_before(self, value: bool) -> None:
        self._derive(page_break_before=value)

    @property
    def tab_stops(self) -> TabStops:
        return TabStops(self._p)


class CellBorder:
    def __init__(self, cell: "Cell"):
        self._cell = cell

    @property
    def _styles(self) -> Styles:
        if self._cell.document is None:
            raise RuntimeError("cell is not attached to a document")
        return self._cell.document.styles

    def _fill(self) -> ElementModel | None:
        return self._styles.border_fill(self._cell.border_fill_id_ref)

    def _derive(self, **kwargs) -> None:
        self._cell.border_fill_id_ref = self._styles.ensure_border_fill(
            base_border_fill_id=self._cell.border_fill_id_ref, **kwargs
        )

    @property
    def color(self) -> str | None:
        bf = self._fill()
        line = None if bf is None else _child(bf, "leftBorder")
        return None if line is None else line.get("color")

    @color.setter
    def color(self, value: str) -> None:
        self._derive(color=value)

    @property
    def width(self) -> str | None:
        bf = self._fill()
        line = None if bf is None else _child(bf, "leftBorder")
        return None if line is None else line.get("width")

    @width.setter
    def width(self, value: str) -> None:
        self._derive(width=value)

    @property
    def type(self) -> str | None:
        bf = self._fill()
        line = None if bf is None else _child(bf, "leftBorder")
        return None if line is None else line.get("type")

    @type.setter
    def type(self, value: str) -> None:
        self._derive(border_type=value)

    @property
    def fill_color(self) -> str | None:
        bf = self._fill()
        brush = None if bf is None else _child(bf, "fillBrush")
        win = None if brush is None else _child(brush, "winBrush")
        if win is None:
            return None
        value = win.get("faceColor")
        return None if value is None or value.lower() == "none" else value

    @fill_color.setter
    def fill_color(self, value: str) -> None:
        self._derive(fill_color=value)
