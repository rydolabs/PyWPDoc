"""High-level structure-preserving literal replacement feature.

This package is independent from sibling features and shares only
lower-level text primitives.
"""
from __future__ import annotations

from typing import Any

from pywpdoc.core import DocumentValueError
from pywpdoc.core.text import (
    TextMap,
    iter_text_map_literal_spans,
    iter_text_paragraphs,
    replace_text_range,
)


def replace_text(
    document: Any,
    search: str,
    replacement: str,
    *,
    everywhere: bool = True,
    case_sensitive: bool = True,
    count: int = -1,
) -> int:
    """Replace literal visible text while preserving surviving inline formatting.

    Matches may span run/hyperlink boundaries.  Inserted text inherits the
    formatting of the first matched visible source.  The feature owns no HWPX
    or DOCX implementation logic; mutation is performed through writable text
    sources exposed by :class:`~pywpdoc.core.text.TextMap`.
    """
    search = str(search)
    replacement = str(replacement)
    if not search:
        raise DocumentValueError("search must not be empty", code="replace-query-empty")

    limit = None if count is None or int(count) < 0 else int(count)
    if limit == 0:
        return 0

    changed = 0
    for paragraph in iter_text_paragraphs(document, everywhere=everywhere):
        if limit is not None and changed >= limit:
            break

        text_map = TextMap.from_paragraph(paragraph)
        if not text_map.text:
            continue

        remaining = -1 if limit is None else limit - changed
        spans = list(
            iter_text_map_literal_spans(
                text_map,
                search,
                case_sensitive=case_sensitive,
                count=remaining,
            )
        )
        if not spans:
            continue

        for span in reversed(spans):
            replace_text_range(text_map, span.start, span.end, replacement)
        changed += len(spans)

    return changed


__all__ = ["replace_text"]
