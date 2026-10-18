"""DOCX style wrappers owned by the standalone DOCX backend.

This module translates only the shared style surface to python-docx.  It does
not know the common facade, the HWPX backend, or paragraph/table/text modules.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterator

from ..core.enums import WD_STYLE_TYPE
from ..core.errors import DocumentValueError, DocumentUnsupportedError
from ..core.proxy import NativeProxy
from ..core.units import Length, Pt


def _imports():
    try:
        from docx.enum.style import WD_STYLE_TYPE as DOCX_STYLE_TYPE
        from docx.shared import Pt as DocxPt, RGBColor
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError("DOCX support requires the optional dependency 'python-docx>=1.2,<2'") from exc
    return DOCX_STYLE_TYPE, DocxPt, RGBColor


def _normalize_style_type(value) -> WD_STYLE_TYPE:
    try:
        return value if isinstance(value, WD_STYLE_TYPE) else WD_STYLE_TYPE(int(value))
    except (TypeError, ValueError) as exc:
        raise DocumentValueError("invalid style type", code="style-type-invalid") from exc


def _unwrap_style(value):
    return value.native if isinstance(value, Style) else value


class StyleFont(NativeProxy):
    """Small backend-owned font surface for a DOCX style."""

    @property
    def size(self) -> Length | None:
        value = self.native.size
        return None if value is None else Pt(value.pt)

    @size.setter
    def size(self, value) -> None:
        if value is None:
            self.native.size = None
            return
        _, DocxPt, _ = _imports()
        points = value.pt if hasattr(value, "pt") else float(value)
        self.native.size = DocxPt(float(points))

    @property
    def color(self) -> str | None:
        rgb = self.native.color.rgb
        return None if rgb is None else f"#{rgb}"

    @color.setter
    def color(self, value: str | None) -> None:
        if value is None:
            self.native.color.rgb = None
            return
        _, _, RGBColor = _imports()
        raw = str(value).strip().lstrip("#")
        if len(raw) != 6:
            raise DocumentValueError("color must be #RRGGBB", code="style-color-invalid")
        try:
            self.native.color.rgb = RGBColor.from_string(raw.upper())
        except ValueError as exc:
            raise DocumentValueError("color must be #RRGGBB", code="style-color-invalid") from exc


class StyleParagraphFormat(NativeProxy):
    """Paragraph formatting wrapper with backend-neutral physical lengths."""

    @staticmethod
    def _to_core(value):
        return None if value is None else Pt(value.pt)

    @staticmethod
    def _to_native(value):
        if value is None:
            return None
        _, DocxPt, _ = _imports()
        points = value.pt if hasattr(value, "pt") else float(value)
        return DocxPt(float(points))

    space_before = property(
        lambda self: self._to_core(self.native.space_before),
        lambda self, value: setattr(self.native, "space_before", self._to_native(value)),
    )
    space_after = property(
        lambda self: self._to_core(self.native.space_after),
        lambda self, value: setattr(self.native, "space_after", self._to_native(value)),
    )


class Style(NativeProxy):
    """Backend-owned DOCX style facade."""

    def __init__(self, native: Any, styles: "Styles"):
        super().__init__(native)
        object.__setattr__(self, "_styles", styles)

    @property
    def name(self) -> str | None:
        return self.native.name

    @name.setter
    def name(self, value: str) -> None:
        self.native.name = value

    @property
    def id(self) -> str:
        return self.native.style_id

    @property
    def style_id(self) -> str:
        return self.native.style_id

    @property
    def style_type(self) -> WD_STYLE_TYPE:
        return WD_STYLE_TYPE(int(self.native.type))

    @property
    def type(self) -> WD_STYLE_TYPE:
        return self.style_type

    @property
    def font(self) -> StyleFont:
        return StyleFont(self.native.font)

    @property
    def paragraph_format(self) -> StyleParagraphFormat:
        return StyleParagraphFormat(self.native.paragraph_format)

    @property
    def next_paragraph_style(self) -> "Style":
        if self.style_type != WD_STYLE_TYPE.PARAGRAPH:
            raise DocumentUnsupportedError(
                "next_paragraph_style is only valid for paragraph styles",
                code="style-next-not-paragraph",
            )
        return self._styles._wrap(self.native.next_paragraph_style)

    @next_paragraph_style.setter
    def next_paragraph_style(self, value) -> None:
        if self.style_type != WD_STYLE_TYPE.PARAGRAPH:
            raise DocumentUnsupportedError(
                "next_paragraph_style is only valid for paragraph styles",
                code="style-next-not-paragraph",
            )
        self.native.next_paragraph_style = _unwrap_style(value)

    def delete(self) -> None:
        self.native.delete()


class Styles(NativeProxy):
    """DOCX style collection implementing the backend's small shared contract."""

    def _wrap(self, native) -> Style:
        return Style(native, self)

    def __getitem__(self, key) -> Style:
        return self._wrap(self.native[key])

    def __iter__(self) -> Iterator[Style]:
        return (self._wrap(style) for style in self.native)

    def __len__(self) -> int:
        return len(self.native)

    def __contains__(self, key: object) -> bool:
        try:
            self.resolve(key)
        except (KeyError, ValueError, TypeError):
            return False
        return True

    def names(self) -> list[str]:
        return [style.name for style in self if style.name]

    def get(self, key, default=None):
        try:
            return self.resolve(key)
        except (KeyError, ValueError, TypeError):
            return default

    def resolve(self, key) -> Style:
        if isinstance(key, Style):
            return key
        if key is None:
            raise KeyError(key)
        if hasattr(key, "style_id") and not isinstance(key, (str, bytes)):
            return self._wrap(key)
        if isinstance(key, int):
            key = str(key)
        raw = str(key)
        # python-docx collection lookup is by name. Support style_id too for a
        # compact backend contract useful to adapters and tests.
        try:
            return self[raw]
        except KeyError:
            for style in self:
                if style.style_id == raw:
                    return style
            raise

    def default(self, style_type) -> Style | None:
        DOCX_STYLE_TYPE = _imports()[0]
        common = _normalize_style_type(style_type)
        native = self.native.default(DOCX_STYLE_TYPE(int(common)))
        return None if native is None else self._wrap(native)

    @staticmethod
    def _copy_direct_formatting(source, target) -> None:
        """Copy direct rPr/pPr only; no cross-style inheritance coupling."""
        src = source._element
        dst = target._element
        if src.rPr is not None:
            dst._remove_rPr()
            dst.append(deepcopy(src.rPr))
        if src.pPr is not None:
            dst._remove_pPr()
            dst.append(deepcopy(src.pPr))

    def add_style(self, name: str, style_type=WD_STYLE_TYPE.PARAGRAPH, builtin: bool = False, *, clone_from=None) -> Style:
        DOCX_STYLE_TYPE = _imports()[0]
        common = _normalize_style_type(style_type)
        source = self.resolve(clone_from) if clone_from is not None else None
        if source is not None and source.style_type != common:
            raise DocumentValueError("clone_from style type must match", code="style-clone-type-mismatch")
        native = self.native.add_style(str(name), DOCX_STYLE_TYPE(int(common)), builtin=builtin)
        if source is not None:
            self._copy_direct_formatting(source.native, native)
        return self._wrap(native)


__all__ = ["Styles", "Style", "StyleFont", "StyleParagraphFormat", "_unwrap_style"]
