"""Small backend-neutral literal matching primitives."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterator


@dataclass(frozen=True)
class TextSpan:
    """One literal match in a logical text stream."""

    start: int
    end: int
    text: str


def iter_literal_spans(
    text: str,
    query: str,
    *,
    case_sensitive: bool = True,
    count: int = -1,
) -> Iterator[TextSpan]:
    """Yield non-overlapping literal matches in left-to-right order."""
    limit = None if count is None or int(count) < 0 else int(count)
    if limit == 0:
        return
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(re.escape(query), flags)
    emitted = 0
    for match in pattern.finditer(text):
        yield TextSpan(match.start(), match.end(), match.group(0))
        emitted += 1
        if limit is not None and emitted >= limit:
            return


def iter_text_map_literal_spans(
    text_map: Any,
    query: str,
    *,
    case_sensitive: bool = True,
    count: int = -1,
) -> Iterator[TextSpan]:
    """Yield literal matches that do not cross unsafe fragment boundaries.

    The helper intentionally uses only the small ``TextMap`` surface rather
    than importing a backend type.  Unsafe matches do not consume ``count``;
    later safe matches can still satisfy the requested limit.
    """

    limit = None if count is None or int(count) < 0 else int(count)
    if limit == 0:
        return
    emitted = 0
    for span in iter_literal_spans(
        text_map.text,
        query,
        case_sensitive=case_sensitive,
        count=-1,
    ):
        if not text_map.is_safe_range(span.start, span.end):
            continue
        yield span
        emitted += 1
        if limit is not None and emitted >= limit:
            return


__all__ = ["TextSpan", "iter_literal_spans", "iter_text_map_literal_spans"]
