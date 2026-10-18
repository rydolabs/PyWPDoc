"""DOCX section facade isolated from the backend document module."""
from __future__ import annotations
from typing import Any

from ..core.proxy import NativeProxy
from ..core import defaults
from ..core.enums import WD_ORIENT
from ..core.errors import DocumentValueError
from ..core.units import Mm
from .story import HeaderFooter


def _docx_section_imports():
    try:
        from docx.shared import Mm as DocxMm
        from docx.enum.section import WD_ORIENT as DOCX_ORIENT
    except ImportError as exc:  # pragma: no cover
        raise ImportError("DOCX support requires the optional dependency 'python-docx>=1.2,<2'") from exc
    return DocxMm, DOCX_ORIENT


def configure_new_document_layout(native: Any) -> None:
    DocxMm, _ = _docx_section_imports()
    section = native.sections[-1]
    section.page_width = DocxMm(defaults.PAGE_WIDTH_MM)
    section.page_height = DocxMm(defaults.PAGE_HEIGHT_MM)
    section.left_margin = DocxMm(defaults.LEFT_MARGIN_MM)
    section.right_margin = DocxMm(defaults.RIGHT_MARGIN_MM)
    section.top_margin = DocxMm(defaults.TOP_MARGIN_MM)
    section.bottom_margin = DocxMm(defaults.BOTTOM_MARGIN_MM)
    section.header_distance = DocxMm(defaults.HEADER_DISTANCE_MM)
    section.footer_distance = DocxMm(defaults.FOOTER_DISTANCE_MM)
    section.gutter = DocxMm(0)


class Section(NativeProxy):
    @staticmethod
    def _to_core_length(value):
        if value is None:
            return None
        return Mm(value.mm)

    @staticmethod
    def _to_native_length(value):
        DocxMm, _ = _docx_section_imports()
        if value is None:
            return None
        if hasattr(value, "mm"):
            return DocxMm(float(value.mm))
        return DocxMm(float(value))

    page_width = property(lambda self: self._to_core_length(self.native.page_width), lambda self, v: setattr(self.native, "page_width", self._to_native_length(v)))
    page_height = property(lambda self: self._to_core_length(self.native.page_height), lambda self, v: setattr(self.native, "page_height", self._to_native_length(v)))
    left_margin = property(lambda self: self._to_core_length(self.native.left_margin), lambda self, v: setattr(self.native, "left_margin", self._to_native_length(v)))
    right_margin = property(lambda self: self._to_core_length(self.native.right_margin), lambda self, v: setattr(self.native, "right_margin", self._to_native_length(v)))
    top_margin = property(lambda self: self._to_core_length(self.native.top_margin), lambda self, v: setattr(self.native, "top_margin", self._to_native_length(v)))
    bottom_margin = property(lambda self: self._to_core_length(self.native.bottom_margin), lambda self, v: setattr(self.native, "bottom_margin", self._to_native_length(v)))
    header_distance = property(lambda self: self._to_core_length(self.native.header_distance), lambda self, v: setattr(self.native, "header_distance", self._to_native_length(v)))
    footer_distance = property(lambda self: self._to_core_length(self.native.footer_distance), lambda self, v: setattr(self.native, "footer_distance", self._to_native_length(v)))
    gutter = property(lambda self: self._to_core_length(self.native.gutter), lambda self, v: setattr(self.native, "gutter", self._to_native_length(v)))

    @property
    def orientation(self):
        value = self.native.orientation
        return WD_ORIENT.PORTRAIT if value is None else WD_ORIENT(int(value))

    @orientation.setter
    def orientation(self, value) -> None:
        _, DOCX_ORIENT = _docx_section_imports()
        try:
            common = value if isinstance(value, WD_ORIENT) else WD_ORIENT(int(value))
        except (TypeError, ValueError) as exc:
            raise DocumentValueError("orientation must be PORTRAIT or LANDSCAPE", code="section-orientation-invalid") from exc
        self.native.orientation = DOCX_ORIENT(int(common))

    def _enable_even_odd(self) -> None:
        # Word only renders the even-page story when this document-level switch
        # is on.  The standalone backend makes accessing the explicit even-page
        # story operational rather than exposing a silent python-docx default.
        self.native._document_part.document.settings.odd_and_even_pages_header_footer = True

    @property
    def header(self) -> HeaderFooter:
        return HeaderFooter(self.native.header, self, "header", "BOTH")

    @property
    def footer(self) -> HeaderFooter:
        return HeaderFooter(self.native.footer, self, "footer", "BOTH")

    @property
    def even_page_header(self) -> HeaderFooter:
        self._enable_even_odd()
        return HeaderFooter(self.native.even_page_header, self, "header", "EVEN")

    @property
    def even_page_footer(self) -> HeaderFooter:
        self._enable_even_odd()
        return HeaderFooter(self.native.even_page_footer, self, "footer", "EVEN")

    @property
    def first_page_header(self) -> HeaderFooter:
        self.native.different_first_page_header_footer = True
        return HeaderFooter(self.native.first_page_header, self, "header", "FIRST")

    @property
    def first_page_footer(self) -> HeaderFooter:
        self.native.different_first_page_header_footer = True
        return HeaderFooter(self.native.first_page_footer, self, "footer", "FIRST")


__all__ = ["Section", "configure_new_document_layout"]
