"""Thin standalone HWPX section adapter over the native HWPX engine."""
from __future__ import annotations

from ..core.proxy import NativeProxy
from .paragraph import Paragraph
from .story import HeaderFooter


class Section(NativeProxy):
    page_width = property(lambda self: self.native.page_width, lambda self, v: setattr(self.native, "page_width", v))
    page_height = property(lambda self: self.native.page_height, lambda self, v: setattr(self.native, "page_height", v))
    left_margin = property(lambda self: self.native.left_margin, lambda self, v: setattr(self.native, "left_margin", v))
    right_margin = property(lambda self: self.native.right_margin, lambda self, v: setattr(self.native, "right_margin", v))
    top_margin = property(lambda self: self.native.top_margin, lambda self, v: setattr(self.native, "top_margin", v))
    bottom_margin = property(lambda self: self.native.bottom_margin, lambda self, v: setattr(self.native, "bottom_margin", v))
    header_distance = property(lambda self: self.native.header_distance, lambda self, v: setattr(self.native, "header_distance", v))
    footer_distance = property(lambda self: self.native.footer_distance, lambda self, v: setattr(self.native, "footer_distance", v))
    gutter = property(lambda self: self.native.gutter, lambda self, v: setattr(self.native, "gutter", v))
    orientation = property(lambda self: self.native.orientation, lambda self, v: setattr(self.native, "orientation", v))

    @property
    def paragraphs(self) -> list[Paragraph]:
        return [Paragraph(p) for p in self.native.paragraphs]

    def add_paragraph(self, text: str = "", style=None, **kwargs) -> Paragraph:
        return Paragraph(self.native.add_paragraph(text, style=getattr(style, "native", style), **kwargs))

    def _wrap_story(self, story):
        return None if story is None else HeaderFooter(story, self)

    def get_header(self, page_type: str = "BOTH"):
        return self._wrap_story(self.native.get_header(page_type))

    def get_footer(self, page_type: str = "BOTH"):
        return self._wrap_story(self.native.get_footer(page_type))

    def set_header_text(self, text: str, page_type: str = "BOTH") -> HeaderFooter:
        return HeaderFooter(self.native.set_header_text(text, page_type), self)

    def set_footer_text(self, text: str, page_type: str = "BOTH") -> HeaderFooter:
        return HeaderFooter(self.native.set_footer_text(text, page_type), self)

    header = property(lambda self: HeaderFooter(self.native.header, self))
    footer = property(lambda self: HeaderFooter(self.native.footer, self))
    even_page_header = property(lambda self: HeaderFooter(self.native.even_page_header, self))
    even_page_footer = property(lambda self: HeaderFooter(self.native.even_page_footer, self))
    odd_page_header = property(lambda self: HeaderFooter(self.native.odd_page_header, self))
    odd_page_footer = property(lambda self: HeaderFooter(self.native.odd_page_footer, self))
    first_page_header = property(lambda self: self.native.first_page_header)
    first_page_footer = property(lambda self: self.native.first_page_footer)


__all__ = ["Section"]
