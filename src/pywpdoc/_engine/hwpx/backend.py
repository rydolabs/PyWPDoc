"""Independent HWPX backend facade.

This module owns HWPX-specific implementation choices for the shared contract.
It never imports the DOCX backend or the common facade. The mature native HWPX
engine remains available through ``.native`` for expert use.
"""
from __future__ import annotations
from pathlib import Path
import copy
from typing import Any

from ..document import Document as NativeDocument
from .paragraph import Paragraph, Run
from .table import Table, Row, Cell, create_document_table
from .text import replace_document
from .styles import Styles, _unwrap_style
from .section import Section
from .media import Picture, create_document_picture
from .metadata import CoreProperties
from .snapshot import export_snapshot as _export_snapshot, import_snapshot as _import_snapshot




class Document:
    """Standalone HWPX backend API implementing the small shared contract."""

    format = "hwpx"

    def __init__(self, native: NativeDocument):
        self.native = native

    @classmethod
    def open(cls, source: str | Path) -> "Document":
        return cls(NativeDocument.open(source))

    @classmethod
    def new(cls, *, compatibility: str = "hancom2020") -> "Document":
        # Compatibility selection remains backend-owned. The default is a
        # real Hancom 2020-authored blank skeleton; ``latest`` preserves the
        # previous 13.x skeleton for explicit opt-in callers.
        return cls(NativeDocument.new(compatibility=compatibility))

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
        return [Picture(p) for p in self.native.pictures]

    @property
    def core_properties(self) -> CoreProperties:
        return CoreProperties(self.native.core_properties)

    @property
    def styles(self) -> Styles:
        return Styles(self.native.styles)

    @property
    def settings(self):
        return self.native.settings

    def add_paragraph(self, text: str = "", style=None) -> Paragraph:
        return Paragraph(self.native.add_paragraph(text, style=_unwrap_style(style)))

    def add_table(self, rows: int, cols: int, style=None) -> Table:
        return create_document_table(self.native, rows, cols, style=style)

    def add_section(self, *, after: int | None = None) -> Section:
        return Section(self.native.add_section(after=after))

    def add_picture(
        self, image_data: bytes, image_format: str, *, width=14400,
        height=None, treat_as_char: bool = True,
    ) -> Picture:
        return create_document_picture(
            self.native, image_data, image_format, width=width, height=height,
            treat_as_char=treat_as_char,
        )


    def export_snapshot(self, *, preserve_layout: bool = True):
        return _export_snapshot(self.native, preserve_layout=preserve_layout)

    def import_snapshot(self, snapshot, *, preserve_layout: bool = True) -> None:
        self.native = _import_snapshot(snapshot, preserve_layout=preserve_layout)

    def replace(self, search: str, replacement: str, *, everywhere: bool = True, count: int = -1) -> int:
        return replace_document(self.native, search, replacement, everywhere=everywhere, count=count)

    def iter_text_paragraphs(self, *, everywhere: bool = True):
        """Yield backend-owned paragraph wrappers for high-level text features."""
        native_paragraphs = self.native._replace_paragraphs(everywhere=everywhere)
        for paragraph in native_paragraphs:
            yield Paragraph(paragraph)

    def iter_tables(self, *, everywhere: bool = True):
        """Yield backend-owned tables for structure-aware high-level features."""
        native_tables = self.native.all_tables if everywhere else self.native.tables
        for table in native_tables:
            yield Table(table)

    def excluded_native_signature(self):
        from .comparison_safety import table_properties_signature, image_objects_signature
        return (table_properties_signature(self), image_objects_signature(self))

    def clone_for_compare(self) -> "Document":
        """Return an in-memory copy without mutating the source document."""
        return type(self)(copy.deepcopy(self.native))

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
