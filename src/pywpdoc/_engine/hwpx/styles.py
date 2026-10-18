"""HWPX style wrappers owned by the standalone HWPX backend.

The mature native HWPX style engine remains the implementation.  This module is
only the standalone backend boundary and does not depend on common/DOCX or on
paragraph/table/text wrappers.
"""
from __future__ import annotations

from typing import Iterator

from ..core.enums import WD_STYLE_TYPE
from ..core.proxy import NativeProxy


def _unwrap_style(value):
    return value.native if isinstance(value, Style) else value


class StyleFont(NativeProxy):
    pass


class StyleParagraphFormat(NativeProxy):
    pass


class Style(NativeProxy):
    def __init__(self, native, styles: "Styles"):
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
        return self.native.id

    @property
    def style_id(self) -> str:
        return self.native.id

    @property
    def style_type(self) -> WD_STYLE_TYPE | None:
        return self.native.style_type

    @property
    def type(self) -> WD_STYLE_TYPE | None:
        return self.style_type

    @property
    def font(self) -> StyleFont:
        return StyleFont(self.native.font)

    @property
    def paragraph_format(self) -> StyleParagraphFormat:
        return StyleParagraphFormat(self.native.paragraph_format)

    @property
    def next_paragraph_style(self) -> "Style":
        return self._styles._wrap(self.native.next_paragraph_style)

    @next_paragraph_style.setter
    def next_paragraph_style(self, value) -> None:
        self.native.next_paragraph_style = _unwrap_style(value)

    def delete(self) -> None:
        self.native.delete()


class Styles(NativeProxy):
    def _wrap(self, native) -> Style:
        return Style(native, self)

    def __getitem__(self, key) -> Style:
        return self._wrap(self.native[key])

    def __iter__(self) -> Iterator[Style]:
        return (self._wrap(style) for style in self.native)

    def __len__(self) -> int:
        return len(self.native)

    def __contains__(self, key: object) -> bool:
        return key in self.native

    def names(self) -> list[str]:
        return self.native.names()

    def get(self, key, default=None):
        if isinstance(key, Style):
            return key
        native = self.native.get(_unwrap_style(key), None)
        return default if native is None else self._wrap(native)

    def resolve(self, key) -> Style:
        if isinstance(key, Style):
            return key
        return self._wrap(self.native.resolve(_unwrap_style(key)))

    def default(self, style_type) -> Style | None:
        native = self.native.default(style_type)
        return None if native is None else self._wrap(native)

    def add_style(self, name: str, style_type=WD_STYLE_TYPE.PARAGRAPH, builtin: bool = False, *, clone_from=None) -> Style:
        native = self.native.add_style(
            name,
            style_type,
            builtin=builtin,
            clone_from=_unwrap_style(clone_from),
        )
        return self._wrap(native)


__all__ = ["Styles", "Style", "StyleFont", "StyleParagraphFormat", "_unwrap_style"]
