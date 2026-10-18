"""Backend-neutral logical text mapping for one paragraph.

The map turns backend-provided :class:`TextFragment` objects into one logical
string while retaining source-object ranges.  It also records *unsafe join
boundaries* where native structure (field/revision/content-control/object, for
example) must prevent a search/template token from spanning across it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .fragments import iter_text_fragments


@dataclass(frozen=True)
class TextSegment:
    """One writable fragment's range in a paragraph logical-text stream."""

    source: Any
    start: int
    end: int
    text: str
    kind: str = "text"


@dataclass(frozen=True)
class TextMap:
    """Logical paragraph text plus source ranges and structural boundaries."""

    text: str
    segments: tuple[TextSegment, ...]
    unsafe_boundaries: tuple[int, ...] = ()

    @classmethod
    def from_paragraph(cls, paragraph: Any) -> "TextMap":
        segments: list[TextSegment] = []
        chunks: list[str] = []
        unsafe_boundaries: list[int] = []
        offset = 0

        for fragment in iter_text_fragments(paragraph):
            value = fragment.text
            if not value:
                continue
            if segments and not fragment.safe_join_before:
                unsafe_boundaries.append(offset)
            start = offset
            offset += len(value)
            chunks.append(value)
            segments.append(
                TextSegment(
                    fragment.source,
                    start,
                    offset,
                    value,
                    fragment.kind,
                )
            )

        return cls(
            "".join(chunks),
            tuple(segments),
            tuple(unsafe_boundaries),
        )

    def sources_for(self, start: int, end: int) -> tuple[TextSegment, ...]:
        """Return visible text segments intersecting ``[start, end)``."""
        if start < 0 or end < start or end > len(self.text):
            raise ValueError("text range is outside the logical paragraph text")
        if start == end:
            return ()
        return tuple(
            segment
            for segment in self.segments
            if segment.end > start and segment.start < end
        )

    def crosses_unsafe_boundary(self, start: int, end: int) -> bool:
        """Return whether ``[start, end)`` crosses an opaque native boundary."""
        if start < 0 or end < start or end > len(self.text):
            raise ValueError("text range is outside the logical paragraph text")
        return any(start < boundary < end for boundary in self.unsafe_boundaries)

    def is_safe_range(self, start: int, end: int) -> bool:
        """Return whether a logical range may be treated as contiguous text."""
        return not self.crosses_unsafe_boundary(start, end)


__all__ = ["TextMap", "TextSegment"]
