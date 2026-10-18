"""Thin standalone HWPX header/footer adapter over the native story engine."""
from __future__ import annotations
from typing import Any

from ..core.proxy import NativeProxy
from .paragraph import Paragraph, Run
from .table import Table


def _unwrap(value):
    return getattr(value, "native", value)


class HeaderFooter(NativeProxy):
    def __init__(self, native: Any, section: Any):
        super().__init__(native)
        object.__setattr__(self, "section", section)

    @property
    def story_kind(self) -> str:
        return self.native.story_kind

    @property
    def apply_page_type(self) -> str:
        return self.native.apply_page_type

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

    text = property(lambda self: self.native.text, lambda self, value: setattr(self.native, "text", str(value)))

    def clear_content(self) -> None:
        self.native.clear_content()

    def add_paragraph(self, text: str = "", style=None, **kwargs) -> Paragraph:
        return Paragraph(self.native.add_paragraph(text, style=_unwrap(style), **kwargs))

    def add_table(self, rows: int, cols: int, style=None, **kwargs) -> Table:
        return Table(self.native.add_table(rows, cols, style=_unwrap(style), **kwargs))

    def add_run(self, text: str, *, paragraph: Paragraph | None = None, **kwargs) -> Run:
        return Run(self.native.add_run(text, paragraph=None if paragraph is None else paragraph.native, **kwargs))

    def add_date_field(self, cached_text: str, *, paragraph: Paragraph | None = None, **kwargs):
        return self.native.add_date_field(cached_text, paragraph=None if paragraph is None else paragraph.native, **kwargs)

    def add_path_field(self, cached_text: str, *, paragraph: Paragraph | None = None):
        return self.native.add_path_field(cached_text, paragraph=None if paragraph is None else paragraph.native)

    def add_page_number_field(self, *, paragraph: Paragraph | None = None, **kwargs):
        return self.native.add_page_number_field(paragraph=None if paragraph is None else paragraph.native, **kwargs)

    def add_page_total_field(self, *, paragraph: Paragraph | None = None, **kwargs):
        return self.native.add_page_total_field(paragraph=None if paragraph is None else paragraph.native, **kwargs)


__all__ = ["HeaderFooter"]
