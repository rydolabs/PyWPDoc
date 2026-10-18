"""Thin optional facade over independently usable DOCX and HWPX backends.

The common layer deliberately owns no text-replacement algorithm, table
geometry, XML handling, or backend option normalization. It only selects a
backend and delegates the shared surface.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

from ..core.errors import DocumentUnsupportedError, DocumentValueError
from ..core.contracts import DocumentBackend


class Document:
    """Thin common wrapper around a standalone backend document."""

    def __init__(self, backend: DocumentBackend):
        self.backend = backend

    @classmethod
    def open(cls, source: str | Path) -> "Document":
        path = Path(source)
        suffix = path.suffix.lower()
        if suffix == ".hwpx":
            from ..hwpx import Document as HwpxDocument
            return cls(HwpxDocument.open(path))
        if suffix == ".docx":
            from ..docx import Document as DocxDocument
            return cls(DocxDocument.open(path))
        raise DocumentValueError(
            f"cannot infer document format from {path.name!r}",
            code="common-format-unknown",
            context={"suffix": suffix},
        )

    @classmethod
    def new(cls, format: str = "hwpx", *, compatibility: str | None = None) -> "Document":
        fmt = str(format).lower().lstrip(".")
        if fmt == "hwpx":
            from ..hwpx import Document as HwpxDocument
            return cls(HwpxDocument.new(compatibility=compatibility or "hancom2020"))
        if fmt == "docx":
            if compatibility is not None:
                raise DocumentValueError(
                    "compatibility profiles are only supported for HWPX",
                    code="common-compatibility-not-applicable",
                    context={"format": fmt, "compatibility": compatibility},
                )
            from ..docx import Document as DocxDocument
            return cls(DocxDocument.new())
        raise DocumentValueError("format must be 'hwpx' or 'docx'", code="common-format-invalid")

    @classmethod
    def rebuild(
        cls,
        source: "Document | str | Path",
        *,
        format: str | None = None,
        preserve_layout: bool = True,
    ) -> "Document":
        """Rebuild *source* through the selected backend.

        Common only transports the backend-neutral snapshot. Export/import
        semantics and all format fidelity rules remain backend-owned.
        """
        src = source if isinstance(source, cls) else cls.open(source)
        target = cls.new(format or src.format)
        snapshot = src.backend.export_snapshot(preserve_layout=preserve_layout)
        if src.format == "docx" and target.format == "hwpx":
            raise DocumentUnsupportedError(
                "DOCX to HWPX rebuild is not supported: no verified portable snapshot importer",
                code="rebuild-docx-to-hwpx-unsupported",
            )
        target.backend.import_snapshot(snapshot, preserve_layout=preserve_layout)
        return target

    def export_snapshot(self, *, preserve_layout: bool = True):
        return self.backend.export_snapshot(preserve_layout=preserve_layout)

    def rebuild_from(self, source: "Document", *, preserve_layout: bool = True) -> "Document":
        snapshot = source.backend.export_snapshot(preserve_layout=preserve_layout)
        if source.format == "docx" and self.format == "hwpx":
            raise DocumentUnsupportedError(
                "DOCX to HWPX rebuild is not supported: no verified portable snapshot importer",
                code="rebuild-docx-to-hwpx-unsupported",
            )
        self.backend.import_snapshot(snapshot, preserve_layout=preserve_layout)
        return self

    @property
    def format(self) -> str:
        return self.backend.format

    @property
    def native(self) -> Any:
        """Deep native/expert object (legacy HWPX Document or python-docx Document)."""
        return self.backend.native

    def unwrap(self) -> Any:
        """Return the current backend/native object via an explicit escape hatch.

        Code using this method is backend-specific and therefore has weaker
        compatibility guarantees than the common or format-specific API.
        """
        return self.native

    @property
    def hwpx(self):
        if self.format != "hwpx":
            raise DocumentUnsupportedError(
                "this document uses the DOCX backend; HWPX expert API is unavailable",
                code="common-hwpx-expert-unavailable",
            )
        return self.native

    @property
    def docx(self):
        if self.format != "docx":
            raise DocumentUnsupportedError(
                "this document uses the HWPX backend; DOCX expert API is unavailable",
                code="common-docx-expert-unavailable",
            )
        return self.native

    def __getattr__(self, name: str):
        # Backend implementation remains independent of the small common facade.
        return getattr(self.backend, name)


UnifiedDocument = Document

__all__ = ["Document", "UnifiedDocument"]
