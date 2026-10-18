"""Standalone DOCX picture/media wrappers.

This module contains all DOCX-specific picture unit translation and insertion
policy used by the standalone backend.  Common never handles python-docx shape
objects or EMU conversion directly.
"""
from __future__ import annotations
from io import BytesIO
from typing import Any

from ..core.errors import DocumentUnsupportedError
from ..core.proxy import NativeProxy
from ..core.units import Mm


def _docx_imports():
    try:
        from docx.enum.shape import WD_INLINE_SHAPE_TYPE
        from docx.shared import Emu
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError("DOCX support requires the optional dependency 'python-docx>=1.2,<2'") from exc
    return WD_INLINE_SHAPE_TYPE, Emu


def _to_core_length(value):
    if value is None:
        return None
    return Mm(value.mm) if hasattr(value, "mm") else value


def _to_native_length(value):
    if value is None:
        return None
    _, Emu = _docx_imports()
    if hasattr(value, "mm"):
        return Emu(round(float(value.mm) * 36000))
    # Backend-neutral bare integer lengths retain the HWPUNIT convention.
    return Emu(round(float(value) * 127))


class Picture(NativeProxy):
    """Backend-owned adapter over python-docx ``InlineShape``."""

    @property
    def width(self):
        return _to_core_length(self.native.width)

    @width.setter
    def width(self, value) -> None:
        self.native.width = _to_native_length(value)

    @property
    def height(self):
        return _to_core_length(self.native.height)

    @height.setter
    def height(self, value) -> None:
        self.native.height = _to_native_length(value)

    @property
    def size(self):
        return self.width, self.height

    def resize(self, *, width=None, height=None) -> "Picture":
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height
        return self


def pictures(document: Any) -> list[Picture]:
    WD_INLINE_SHAPE_TYPE, _ = _docx_imports()
    picture_types = {WD_INLINE_SHAPE_TYPE.PICTURE, WD_INLINE_SHAPE_TYPE.LINKED_PICTURE}
    return [Picture(shape) for shape in document.inline_shapes if shape.type in picture_types]


def create_document_picture(
    document: Any,
    image_data: bytes,
    image_format: str | None = None,
    *,
    width=None,
    height=None,
    treat_as_char: bool = True,
) -> Picture:
    """Insert a body picture using bytes and backend-neutral physical lengths."""
    if not treat_as_char:
        raise DocumentUnsupportedError(
            "DOCX backend currently supports inline pictures only",
            code="docx-floating-picture-unsupported",
        )
    # python-docx detects the actual image format from the stream.  Keep the
    # image_format argument for parity with HWPX, where it is required by the
    # package manifest.
    del image_format
    native = document.add_picture(
        BytesIO(bytes(image_data)),
        width=_to_native_length(width),
        height=_to_native_length(height),
    )
    return Picture(native)


__all__ = ["Picture", "pictures", "create_document_picture"]
