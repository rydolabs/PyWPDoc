"""Pure structural-template model objects.

These types are deliberately not wired into ``render_template`` in v0.26.0.
They let section/repeat syntax and document-structure planning evolve without
changing the stable variable-only v1 renderer.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SectionKind(str, Enum):
    NORMAL = "normal"
    INVERTED = "inverted"


class SectionMarkerKind(str, Enum):
    OPEN = "open"
    INVERTED_OPEN = "inverted-open"
    CLOSE = "close"


@dataclass(frozen=True)
class SectionMarker:
    key: str
    kind: SectionMarkerKind
    start: int
    end: int
    raw: str


@dataclass(frozen=True)
class SectionBlock:
    """One balanced Mustache-style section in a logical text stream."""

    key: str
    kind: SectionKind
    open_marker: SectionMarker
    close_marker: SectionMarker

    @property
    def content_start(self) -> int:
        return self.open_marker.end

    @property
    def content_end(self) -> int:
        return self.close_marker.start


@dataclass(frozen=True)
class TableRowRepeatPlan:
    """Backend-neutral description of a future table-row repetition action.

    The plan refers only to a logical collection key and an opaque row token.
    It intentionally carries no HWPX/DOCX object or XML node.  A backend
    capability will later interpret the row token, clone the template row,
    and render each row with an item context.
    """

    key: str
    row_token: object
    remove_template_row: bool = True
    row_index: int | None = None
    kind: SectionKind = SectionKind.NORMAL


__all__ = [
    "SectionKind", "SectionMarkerKind", "SectionMarker", "SectionBlock",
    "TableRowRepeatPlan",
]
