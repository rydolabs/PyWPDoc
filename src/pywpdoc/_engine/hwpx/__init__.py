"""Standalone HWPX backend facade.

For the full HWPX expert surface, use ``Document.native`` or the legacy
``pywpdoc._engine.Document`` API. This backend is independently usable without
the common facade.
"""
from .backend import Document
from .section import Section
from .story import HeaderFooter
from .paragraph import Paragraph, Run
from .table import Table, Row, Column, Cell
from .styles import Styles, Style, StyleFont, StyleParagraphFormat
from .media import Picture
from .metadata import CoreProperties

__all__ = ["Document", "Paragraph", "Run", "Table", "Row", "Column", "Cell", "Section", "HeaderFooter", "Picture", "CoreProperties", "Styles", "Style", "StyleFont", "StyleParagraphFormat"]
