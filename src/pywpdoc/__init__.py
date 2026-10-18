"""PyWPDoc: Python word-processing document automation API.

Use ``pywpdoc.Document`` for the high-level format-neutral API.
Use ``pywpdoc.hwpx`` or ``pywpdoc.docx`` for backend-specific APIs.
"""
from .document import Document, UnifiedDocument
from .core import (
    Length, Pt, Mm, HwpUnit, Cm, Inches,
    WD_CELL_VERTICAL_ALIGNMENT, WD_ALIGN_VERTICAL,
    WD_ORIENTATION, WD_ORIENT, WD_STYLE_TYPE,
    DocumentError, DocumentValueError, DocumentStateError, DocumentUnsupportedError,
)

from importlib.metadata import PackageNotFoundError as _PackageNotFoundError, version as _pkg_version
try:
    __version__ = _pkg_version("pywpdoc")
except _PackageNotFoundError:
    __version__ = "0+unknown"  # direct source import without installed package metadata

__all__ = [
    "Document", "UnifiedDocument",
    "Length", "Pt", "Mm", "HwpUnit", "Cm", "Inches",
    "WD_CELL_VERTICAL_ALIGNMENT", "WD_ALIGN_VERTICAL",
    "WD_ORIENTATION", "WD_ORIENT", "WD_STYLE_TYPE",
    "DocumentError", "DocumentValueError", "DocumentStateError", "DocumentUnsupportedError",
    "__version__",
]
