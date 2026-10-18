"""Pure parser for future Mustache-style section syntax.

The parser is document-format agnostic and performs no rendering.  v0.25's
public ``render_template`` remains variable-only; this parser exists so the
next structural feature can be developed and tested independently first.
"""
from __future__ import annotations

import re
from collections.abc import Iterator

from pywpdoc.core import DocumentValueError

from .model import SectionBlock, SectionKind, SectionMarker, SectionMarkerKind

_TAG_RE = re.compile(r"{{\s*([#\^/])\s*([^{}]+?)\s*}}", re.DOTALL)


def iter_section_markers(text: str) -> Iterator[SectionMarker]:
    for match in _TAG_RE.finditer(text):
        prefix = match.group(1)
        key = match.group(2).strip()
        if not key:
            raise DocumentValueError(
                "template section name must not be empty",
                code="template-section-empty",
            )
        kind = {
            "#": SectionMarkerKind.OPEN,
            "^": SectionMarkerKind.INVERTED_OPEN,
            "/": SectionMarkerKind.CLOSE,
        }[prefix]
        yield SectionMarker(
            key=key,
            kind=kind,
            start=match.start(),
            end=match.end(),
            raw=match.group(0),
        )


def parse_section_blocks(text: str) -> list[SectionBlock]:
    """Pair nested section markers and return balanced blocks.

    Blocks are returned in opening-marker order.  Mismatched or unbalanced
    sections fail explicitly so a future renderer never guesses structure.
    """
    stack: list[SectionMarker] = []
    completed: list[SectionBlock] = []

    for marker in iter_section_markers(text):
        if marker.kind in (SectionMarkerKind.OPEN, SectionMarkerKind.INVERTED_OPEN):
            stack.append(marker)
            continue

        if not stack:
            raise DocumentValueError(
                f"template section close without opener: {marker.raw}",
                code="template-section-unbalanced",
                context={"key": marker.key, "position": marker.start},
            )
        opener = stack.pop()
        if opener.key != marker.key:
            raise DocumentValueError(
                f"template section mismatch: {opener.key!r} closed by {marker.key!r}",
                code="template-section-mismatch",
                context={"open": opener.key, "close": marker.key},
            )
        completed.append(
            SectionBlock(
                key=opener.key,
                kind=(
                    SectionKind.NORMAL
                    if opener.kind == SectionMarkerKind.OPEN
                    else SectionKind.INVERTED
                ),
                open_marker=opener,
                close_marker=marker,
            )
        )

    if stack:
        opener = stack[-1]
        raise DocumentValueError(
            f"template section is not closed: {opener.raw}",
            code="template-section-unbalanced",
            context={"key": opener.key, "position": opener.start},
        )

    return sorted(completed, key=lambda block: block.open_marker.start)


__all__ = ["iter_section_markers", "parse_section_blocks"]
