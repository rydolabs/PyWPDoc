"""Small reusable text primitives shared by optional feature modules."""
from .fragments import TextFragment, iter_text_fragments
from .map import TextMap, TextSegment
from .match import TextSpan, iter_literal_spans, iter_text_map_literal_spans
from .mutation import replace_text_range
from .traversal import iter_text_paragraphs

__all__ = [
    "TextFragment", "iter_text_fragments",
    "TextMap", "TextSegment", "TextSpan",
    "iter_literal_spans", "iter_text_map_literal_spans",
    "replace_text_range", "iter_text_paragraphs",
]
