"""High-level, format-neutral PyWPDoc document facade.

The documented shared surface is defined explicitly by the common facade.
Advanced backend passthrough is available for expert use, but only the
listed shared operations carry cross-format API guarantees.
"""
from __future__ import annotations
from pathlib import Path
from pywpdoc._engine.core.errors import DocumentValueError

from pywpdoc._engine.common.document import Document as _BaselineDocument


class Document(_BaselineDocument):
    """PyWPDoc's high-level document entry point."""

    # The documented portable surface is defined explicitly below.  Existing
    # backend passthrough remains for compatibility with internal/advanced use,
    # but it is not itself a promise of cross-format API parity.
    @property
    def paragraphs(self):
        """Top-level paragraphs as backend-owned wrappers."""
        return self.backend.paragraphs

    @property
    def tables(self):
        """Top-level tables as backend-owned wrappers."""
        return self.backend.tables

    @property
    def sections(self):
        """Sections as backend-owned wrappers."""
        return self.backend.sections

    @property
    def pictures(self):
        return self.backend.pictures

    @property
    def styles(self):
        return self.backend.styles

    @property
    def core_properties(self):
        return self.backend.core_properties

    def add_paragraph(self, text: str = "", style=None):
        """Append a paragraph using the portable document contract."""
        return self.backend.add_paragraph(text, style=style)

    def add_table(self, rows: int, cols: int, style=None):
        """Append a table and return its backend-owned wrapper."""
        return self.backend.add_table(rows, cols, style=style)

    def add_section(self):
        """Append a section using each format's default section-start rule.

        DOCX ``start_type`` and HWPX ``after`` are expert/backend-specific
        controls, not interchangeable common arguments.
        """
        return self.backend.add_section()

    def add_picture(
        self, image_data: bytes, image_format: str | None = None, *,
        width=None, height=None, treat_as_char: bool = True,
    ):
        """Insert a picture with common arguments.

        Recognizes PNG, JPEG, GIF and BMP signatures when image_format is
        omitted. Explicit width/height may be :class:`pywpdoc.Mm` or common
        HWP units. Without width, the historical backend defaults differ:
        DOCX uses intrinsic size and HWPX uses a 2-inch width. Supply width
        for predictable size on both formats.
        """
        fmt = image_format
        if fmt is None:
            data = bytes(image_data)
            if data.startswith(b"\x89PNG\r\n\x1a\n"):
                fmt = "png"
            elif data.startswith(b"\xff\xd8\xff"):
                fmt = "jpeg"
            elif data.startswith((b"GIF87a", b"GIF89a")):
                fmt = "gif"
            elif data.startswith(b"BM"):
                fmt = "bmp"
            else:
                raise DocumentValueError(
                    "image_format is required for an unrecognized image signature",
                    code="common-image-format-unknown",
                )
        # Preserve the existing HWPX default for width=None (2 inches), as
        # the native engine cannot infer an intrinsic size for every format.
        options = {"height": height, "treat_as_char": treat_as_char}
        if width is not None or self.format == "docx":
            options["width"] = width
        return self.backend.add_picture(image_data, fmt, **options)

    def save(self, path: str | Path) -> None:
        """Save in the document's current format. Does not convert formats."""
        self.backend.save(path)


    def find(
        self, query: str, *, everywhere: bool = True,
        case_sensitive: bool = True, count: int = -1,
    ):
        from .features.find import find
        return find(
            self, query, everywhere=everywhere,
            case_sensitive=case_sensitive, count=count,
        )

    def replace_text(
        self, search: str, replacement: str, *, everywhere: bool = True,
        case_sensitive: bool = True, count: int = -1,
    ) -> int:
        from .features.replace import replace_text
        return replace_text(
            self, search, replacement, everywhere=everywhere,
            case_sensitive=case_sensitive, count=count,
        )

    def preview_replace(
        self, search: str, replacement: str, *, everywhere: bool = True,
        case_sensitive: bool = True, count: int = -1,
    ):
        """Return a read-only report of literal replacement candidates."""
        from .features.replace import preview_replace
        return preview_replace(
            self, search, replacement, everywhere=everywhere,
            case_sensitive=case_sensitive, count=count,
        )

    def find_regex(
        self, pattern: str, *, everywhere: bool = True,
        flags: int = 0, count: int = -1,
    ):
        """Find safe, nonempty regular expression matches in logical text."""
        from .features.regex import find_regex
        return find_regex(
            self, pattern, everywhere=everywhere, flags=flags, count=count,
        )

    def replace_regex(
        self, pattern: str, replacement: str, *, everywhere: bool = True,
        flags: int = 0, count: int = -1,
    ) -> int:
        """Replace regex matches, preserving surviving inline formatting."""
        from .features.regex import replace_regex
        return replace_regex(
            self, pattern, replacement, everywhere=everywhere,
            flags=flags, count=count,
        )

    def render_template(
        self, data, *, everywhere: bool = True, missing: str = "keep",
        sections: bool = False, table_rows: bool = False,
    ) -> int:
        from .features.template import render_template
        return render_template(
            self, data, everywhere=everywhere, missing=missing, sections=sections,
            table_rows=table_rows,
        )

    def check_template(
        self, data, *, everywhere: bool = True,
        sections: bool = False, table_rows: bool = False,
    ):
        """Return a read-only preflight report for source template tags."""
        from .features.template import check_template
        return check_template(
            self, data, everywhere=everywhere,
            sections=sections, table_rows=table_rows,
        )

    def compare(
        self, new, *, author: str = "PyWPDoc", date: str | None = None,
        everywhere: bool = True,
    ):
        """Return a new document with tracked text changes from self -> new."""
        from .features.compare import compare_documents
        return compare_documents(
            self, new, author=author, date=date, everywhere=everywhere,
        )


UnifiedDocument = Document

__all__ = ["Document", "UnifiedDocument"]
