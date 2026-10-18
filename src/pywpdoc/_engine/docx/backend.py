"""Independent DOCX backend facade built on python-docx.

All DOCX-specific option translation lives here. The common facade delegates to
this module and contains no WordprocessingML geometry or mutation logic.
"""
from __future__ import annotations
from pathlib import Path
from io import BytesIO
from typing import Any

from .paragraph import Paragraph, Run
from .table import Table, Row, Cell, create_document_table
from .text import replace_document
from .traversal import iter_search_paragraphs, iter_search_tables, iter_table_tree
from .styles import Styles, _unwrap_style
from .section import Section, configure_new_document_layout
from .media import Picture, pictures as document_pictures, create_document_picture
from .metadata import CoreProperties
from .snapshot import export_snapshot as _export_snapshot, import_snapshot as _import_snapshot


def _docx_imports():
    try:
        from docx import Document as DocxDocument
        from docx.enum.style import WD_STYLE_TYPE as DOCX_STYLE_TYPE
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError("DOCX support requires the optional dependency 'python-docx>=1.2,<2'") from exc
    return DocxDocument, DOCX_STYLE_TYPE




class Document:
    """Standalone DOCX backend API. Usable without the common facade."""

    format = "docx"

    def __init__(self, native: Any):
        self.native = native

    @classmethod
    def open(cls, source: str | Path) -> "Document":
        DocxDocument = _docx_imports()[0]
        return cls(DocxDocument(source))

    @classmethod
    def new(cls) -> "Document":
        DocxDocument = _docx_imports()[0]
        native = DocxDocument()
        configure_new_document_layout(native)
        return cls(native)

    @property
    def paragraphs(self) -> list[Paragraph]:
        return [Paragraph(p) for p in self.native.paragraphs]

    @property
    def tables(self) -> list[Table]:
        return [Table(t) for t in self.native.tables]

    @property
    def sections(self) -> list[Section]:
        return [Section(s) for s in self.native.sections]

    @property
    def pictures(self) -> list[Picture]:
        return document_pictures(self.native)

    @property
    def core_properties(self) -> CoreProperties:
        return CoreProperties(self.native.core_properties)

    @property
    def styles(self) -> Styles:
        return Styles(self.native.styles)

    def add_paragraph(self, text: str = "", style=None) -> Paragraph:
        return Paragraph(self.native.add_paragraph(text, style=_unwrap_style(style)))

    def add_table(self, rows: int, cols: int, style=None) -> Table:
        return create_document_table(self.native, rows, cols, style=style)

    def add_section(self, start_type=None) -> Section:
        if start_type is None:
            native = self.native.add_section()
        else:
            native = self.native.add_section(start_type)
        return Section(native)

    def add_picture(
        self, image_data: bytes, image_format: str | None = None, *, width=None,
        height=None, treat_as_char: bool = True,
    ) -> Picture:
        return create_document_picture(
            self.native, image_data, image_format, width=width, height=height,
            treat_as_char=treat_as_char,
        )


    def export_snapshot(self, *, preserve_layout: bool = True):
        return _export_snapshot(self.native, preserve_layout=preserve_layout)

    def import_snapshot(self, snapshot, *, preserve_layout: bool = True) -> None:
        self.native = _import_snapshot(snapshot)

    def replace(self, search: str, replacement: str, *, everywhere: bool = True, count: int = -1) -> int:
        return replace_document(self.native, search, replacement, everywhere=everywhere, count=count)

    def iter_text_paragraphs(self, *, everywhere: bool = True):
        """Yield backend-owned paragraph wrappers for high-level text features."""
        native_paragraphs = (
            iter_search_paragraphs(self.native)
            if everywhere else iter(self.native.paragraphs)
        )
        for paragraph in native_paragraphs:
            yield Paragraph(paragraph)

    def iter_tables(self, *, everywhere: bool = True):
        """Yield backend-owned tables for structure-aware high-level features."""
        native_tables = (
            iter_search_tables(self.native)
            if everywhere
            else (nested for table in self.native.tables for nested in iter_table_tree(table))
        )
        for table in native_tables:
            yield Table(table)

    def assert_body_revision_paragraphs_safe(self, block_indices):
        """Reject relationship-bearing paragraphs before scope-fingerprint checks."""
        from .revisions import _assert_plain_paragraph
        blocks = list(self.native.iter_inner_content())
        for index in block_indices:
            _assert_plain_paragraph(blocks[index], index)

    def excluded_native_signature(self):
        from .comparison_safety import table_properties_signature, image_objects_signature
        return (table_properties_signature(self), image_objects_signature(self))

    def clone_for_compare(self) -> "Document":
        """Return an in-memory copy without mutating the source document."""
        buffer = BytesIO()
        self.native.save(buffer)
        buffer.seek(0)
        return type(self)(_docx_imports()[0](buffer))

    def apply_revision_plan(self, plan, old_backend, *, author: str, date: str | None = None) -> None:
        from .revisions import apply_revision_plan
        apply_revision_plan(
            self.native, plan, old_backend.native, author=author, date=date,
        )

    def save(self, path: str | Path) -> None:
        self.native.save(path)

    def iter_inner_content(self):
        for item in self.native.iter_inner_content():
            name = type(item).__name__.lower()
            if "paragraph" in name:
                yield Paragraph(item)
            elif "table" in name:
                yield Table(item)
            else:
                yield item

    def __getattr__(self, name: str):
        return getattr(self.native, name)
