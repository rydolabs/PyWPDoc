"""HWPX text operations.

The mature native HWPX engine owns the actual mutation algorithm.  This small
module is the backend boundary for text operations so the HWPX document/paragraph
facades do not need to know how text replacement is implemented internally.
"""
from __future__ import annotations
from typing import Any


def replace_paragraph(native: Any, search: str, replacement: str, count: int = -1) -> int:
    return native.replace(search, replacement, count)


def replace_document(
    native: Any,
    search: str,
    replacement: str,
    *,
    everywhere: bool = True,
    count: int = -1,
) -> int:
    return native.replace(search, replacement, everywhere=everywhere, count=count)


__all__ = ["replace_paragraph", "replace_document"]
