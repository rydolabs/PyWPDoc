"""Stable common types/contracts exposed through the PyWPDoc namespace."""
from pywpdoc._engine.core import *  # noqa: F401,F403
from pywpdoc._engine.core import __all__ as _baseline_all
from .structure import iter_tables
from .text import (
    TextFragment, iter_text_fragments,
    TextMap, TextSegment, TextSpan,
    iter_literal_spans, iter_text_map_literal_spans,
    replace_text_range, iter_text_paragraphs,
)

__all__ = [
    *_baseline_all,
    "TextFragment", "iter_text_fragments",
    "TextMap", "TextSegment", "TextSpan",
    "iter_literal_spans", "iter_text_map_literal_spans",
    "replace_text_range", "iter_text_paragraphs",
    "iter_tables",
]
