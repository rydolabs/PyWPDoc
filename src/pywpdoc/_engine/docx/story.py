"""DOCX header/footer story wrappers.

This module owns the standalone DOCX backend's story surface.  It translates
python-docx header/footer objects into backend-owned Paragraph/Table wrappers
without importing the common facade or the HWPX backend.
"""
from __future__ import annotations
from typing import Any

from ..core.proxy import NativeProxy
from ..core.units import Mm
from .paragraph import Paragraph
from .table import Table
from .table_geometry import configure_table


def _unwrap(value):
    return getattr(value, "native", value)


def _native_length(value):
    try:
        from docx.shared import Mm as DocxMm
    except ImportError as exc:  # pragma: no cover
        raise ImportError("DOCX support requires the optional dependency 'python-docx>=1.2,<2'") from exc
    if value is None:
        return None
    if hasattr(value, "mm"):
        return DocxMm(float(value.mm))
    return DocxMm(float(value))


class HeaderFooter(NativeProxy):
    """Backend-owned wrapper around a python-docx header/footer story."""

    def __init__(self, native: Any, section: Any, kind: str, page_type: str = "BOTH"):
        super().__init__(native)
        object.__setattr__(self, "section", section)
        object.__setattr__(self, "story_kind", kind)
        object.__setattr__(self, "_page_type", str(page_type).upper())

    @property
    def apply_page_type(self) -> str:
        return self._page_type

    @property
    def paragraphs(self) -> list[Paragraph]:
        return [Paragraph(p) for p in self.native.paragraphs]

    @property
    def tables(self) -> list[Table]:
        return [Table(t) for t in self.native.tables]

    def iter_inner_content(self):
        for item in self.native.iter_inner_content():
            name = type(item).__name__.lower()
            if "paragraph" in name:
                yield Paragraph(item)
            elif "table" in name:
                yield Table(item)
            else:
                yield item

    @property
    def text(self) -> str:
        return "\n".join(
            item.text for item in self.iter_inner_content()
            if type(item).__module__.endswith(".paragraph")
        )

    @text.setter
    def text(self, value: str) -> None:
        self.clear_content()
        self.native.paragraphs[0].text = str(value)

    def clear_content(self) -> None:
        """Replace story content with one empty paragraph, preserving the story part."""
        paragraphs = list(self.native.paragraphs)
        if paragraphs:
            keep = paragraphs[0]._p
            paragraphs[0].text = ""
        else:  # pragma: no cover - python-docx stories normally contain one p
            keep = self.native.add_paragraph()._p
        root = self.native._element
        for child in list(root):
            if child is not keep:
                root.remove(child)

    def add_paragraph(self, text: str = "", style=None) -> Paragraph:
        return Paragraph(self.native.add_paragraph(text, style=_unwrap(style)))

    def _content_width(self):
        page_width = self.section.page_width
        left = self.section.left_margin
        right = self.section.right_margin
        return Mm(max(float(page_width.mm) - float(left.mm) - float(right.mm), 0.0))

    def add_table(self, rows: int, cols: int, style=None, *, width=None) -> Table:
        target_width = self._content_width() if width is None else width
        table = self.native.add_table(rows, cols, _native_length(target_width))
        if style is not None:
            table.style = _unwrap(style)
        configure_table(table)
        return Table(table)


__all__ = ["HeaderFooter"]
