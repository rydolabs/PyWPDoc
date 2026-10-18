"""DOCX text operations.

This module owns structure-preserving text mutation for the DOCX backend.  It
knows python-docx paragraph/run objects, but it does not know the common facade,
table wrapper classes, styles wrapper classes, or the HWPX backend.
"""
from __future__ import annotations
from typing import Any, Iterable

from ..core.errors import DocumentValueError


def replace_paragraph(native: Any, search: str, replacement: str, count: int = -1) -> int:
    """Replace text across run boundaries while preserving surviving run formatting."""
    if not search:
        raise DocumentValueError("search must not be empty", code="text-search-empty")
    if count == 0:
        return 0

    runs = list(native.runs)
    texts = [run.text for run in runs]
    combined = "".join(texts)
    starts: list[int] = []
    pos = 0
    for text in texts:
        starts.append(pos)
        pos += len(text)

    matches: list[tuple[int, int]] = []
    cursor = 0
    limit = None if count is None or int(count) < 0 else int(count)
    while True:
        if limit is not None and len(matches) >= limit:
            break
        start = combined.find(search, cursor)
        if start < 0:
            break
        end = start + len(search)
        matches.append((start, end))
        cursor = end
    if not matches:
        return 0

    def locate(index: int) -> tuple[int, int]:
        for i, (base, text) in enumerate(zip(starts, texts)):
            if base <= index < base + len(text):
                return i, index - base
        raise IndexError(index)

    for start, end in reversed(matches):
        first_i, first_off = locate(start)
        last_i, last_off = locate(end - 1)
        if first_i == last_i:
            text = runs[first_i].text
            runs[first_i].text = text[:first_off] + replacement + text[last_off + 1:]
        else:
            first_text = runs[first_i].text
            last_text = runs[last_i].text
            runs[first_i].text = first_text[:first_off] + replacement
            for i in range(first_i + 1, last_i):
                runs[i].text = ""
            runs[last_i].text = last_text[last_off + 1:]
    return len(matches)


def iter_cell_paragraphs(cell: Any) -> Iterable[Any]:
    """Yield paragraphs in a cell, including recursively nested tables."""
    yield from cell.paragraphs
    for table in cell.tables:
        yield from iter_table_paragraphs(table)


def iter_table_paragraphs(table: Any) -> Iterable[Any]:
    """Yield each physical cell's paragraphs once, including nested tables."""
    seen: set[Any] = set()
    for row in table.rows:
        for cell in row.cells:
            # Keep the underlying XML cell node itself as the identity key.
            # ``id(cell._tc)`` is unsafe here because python-docx/lxml may
            # materialize short-lived proxy objects whose Python ids can be
            # reused during iteration, causing unrelated physical cells to be
            # skipped in real Word-authored tables.  The XML node is hashable
            # and repeated merged-cell proxies compare as the same node.
            key = cell._tc
            if key in seen:
                continue
            seen.add(key)
            yield from iter_cell_paragraphs(cell)


def iter_everywhere_paragraphs(document: Any) -> Iterable[Any]:
    """Yield text-bearing DOCX paragraphs across body, tables, headers and footers."""
    yield from document.paragraphs
    for table in document.tables:
        yield from iter_table_paragraphs(table)

    seen_parts: set[int] = set()
    for section in document.sections:
        for story in (
            section.header,
            section.footer,
            section.even_page_header,
            section.even_page_footer,
            section.first_page_header,
            section.first_page_footer,
        ):
            part_key = id(story.part)
            if part_key in seen_parts:
                continue
            seen_parts.add(part_key)
            yield from story.paragraphs
            for table in story.tables:
                yield from iter_table_paragraphs(table)



def replace_document(
    document: Any,
    search: str,
    replacement: str,
    *,
    everywhere: bool = True,
    count: int = -1,
) -> int:
    """Apply the DOCX backend's document-wide structure-preserving replace policy."""
    if not search:
        raise DocumentValueError("search must not be empty", code="text-search-empty")

    remaining = None if count is None or int(count) < 0 else int(count)
    changed = 0
    paragraphs = iter_everywhere_paragraphs(document) if everywhere else iter(document.paragraphs)
    for paragraph in paragraphs:
        if remaining is not None and remaining <= 0:
            break
        n = replace_paragraph(paragraph, search, replacement, -1 if remaining is None else remaining)
        changed += n
        if remaining is not None:
            remaining -= n
    return changed


__all__ = [
    "replace_paragraph",
    "replace_document",
    "iter_cell_paragraphs",
    "iter_table_paragraphs",
    "iter_everywhere_paragraphs",
]
