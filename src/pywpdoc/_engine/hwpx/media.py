"""Standalone HWPX picture/media wrappers.

The mature native HWPX engine continues to own package/manifest insertion and
shape semantics.  This module owns only the standalone backend's Picture type
and backend-facing picture creation boundary.
"""
from __future__ import annotations
from typing import Any

from ..core.proxy import NativeProxy
from ..core.units import HwpUnit


def _to_hwpx_length(value):
    if value is None:
        return None
    if hasattr(value, "mm"):
        return round(float(value.mm) * 7200 / 25.4)
    return int(value)


class Picture(NativeProxy):
    """Backend-owned adapter over a native HWPX ``Picture`` object."""

    @property
    def width(self):
        value = self.native.width
        return None if value is None else HwpUnit(value)

    @width.setter
    def width(self, value) -> None:
        self.native.width = _to_hwpx_length(value)

    @property
    def height(self):
        value = self.native.height
        return None if value is None else HwpUnit(value)

    @height.setter
    def height(self, value) -> None:
        self.native.height = _to_hwpx_length(value)

    @property
    def size(self):
        return self.width, self.height

    def resize(self, *, width=None, height=None) -> "Picture":
        self.native.resize(width=_to_hwpx_length(width), height=_to_hwpx_length(height))
        return self


def create_document_picture(
    document: Any,
    image_data: bytes,
    image_format: str,
    *,
    width=14400,
    height=None,
    treat_as_char: bool = True,
) -> Picture:
    """Create a body picture through the native HWPX media/package engine."""
    native = document.add_picture(
        image_data,
        image_format,
        width=_to_hwpx_length(width),
        height=_to_hwpx_length(height),
        treat_as_char=treat_as_char,
    )
    return Picture(native)


__all__ = ["Picture", "create_document_picture"]
