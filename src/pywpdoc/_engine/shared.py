"""Backward-compatible import location for public length types.

The actual definitions live in :mod:`pywpdoc._engine.core.units` so DOCX,
HWPX, and the optional common facade share the same tiny value-object module.
"""
from .core.units import Length, Pt, Mm, HwpUnit, Cm, Inches

__all__ = ["Length", "Pt", "Mm", "HwpUnit", "Cm", "Inches"]
