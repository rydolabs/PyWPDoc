"""High-level literal text search built only from reusable core primitives."""
from __future__ import annotations

from typing import Any

from pywpdoc.core import DocumentValueError
from pywpdoc.core.text import TextMap, iter_text_map_literal_spans, iter_text_paragraphs

from .model import FindMatch


def find(
    document: Any,
    query: str,
    *,
    everywhere: bool = True,
    case_sensitive: bool = True,
    count: int = -1,
) -> list[FindMatch]:
    """Find literal text, including matches spanning run/hyperlink boundaries."""
    query = str(query)
    if not query:
        raise DocumentValueError("query must not be empty", code="find-query-empty")
    limit = None if count is None or int(count) < 0 else int(count)
    if limit == 0:
        return []

    matches: list[FindMatch] = []
    for paragraph_index, paragraph in enumerate(
        iter_text_paragraphs(document, everywhere=everywhere)
    ):
        text_map = TextMap.from_paragraph(paragraph)
        if not text_map.text:
            continue
        remaining = -1 if limit is None else limit - len(matches)
        for span in iter_text_map_literal_spans(
            text_map, query,
            case_sensitive=case_sensitive,
            count=remaining,
        ):
            matches.append(
                FindMatch(
                    paragraph=paragraph,
                    paragraph_index=paragraph_index,
                    start=span.start,
                    end=span.end,
                    text=span.text,
                )
            )
        if limit is not None and len(matches) >= limit:
            return matches
    return matches


__all__ = ["find"]
