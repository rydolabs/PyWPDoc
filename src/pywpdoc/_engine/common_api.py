"""Compatibility shim for the v0.12 experimental common API import path.

The implementation moved to :mod:`pywpdoc._engine.common` in v0.13. The
common layer is now intentionally thin; all real behavior lives in the
independently usable DOCX/HWPX backend modules.
"""
from .common import Document, UnifiedDocument

__all__ = ["Document", "UnifiedDocument"]
