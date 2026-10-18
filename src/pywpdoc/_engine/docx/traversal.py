"""Read-only DOCX traversal capabilities for high-level feature modules.

This module is deliberately separate from ``text.py`` so historical text
mutation dependencies remain unchanged.  It may use python-docx internals
because it is owned by the DOCX backend, while feature modules never import it.
"""
from __future__ import annotations

from typing import Any, Iterable

from .text import iter_table_paragraphs


def _docx_story_imports():
    try:
        from docx.opc.constants import RELATIONSHIP_TYPE as RT
        from docx.table import Table as NativeTable
        from docx.text.paragraph import Paragraph as NativeParagraph
        from docx.oxml.ns import qn
    except ImportError as exc:  # pragma: no cover - optional DOCX dependency
        raise ImportError("DOCX support requires the optional dependency 'python-docx>=1.2,<2'") from exc
    return RT, NativeTable, NativeParagraph, qn


def _iter_existing_story_blocks(document: Any):
    """Yield existing header/footer blocks without creating missing parts."""
    RT, NativeTable, NativeParagraph, qn = _docx_story_imports()
    seen_parts: set[int] = set()
    for relationship in document.part.rels.values():
        if relationship.reltype not in {RT.HEADER, RT.FOOTER}:
            continue
        part = relationship.target_part
        part_key = id(part)
        if part_key in seen_parts:
            continue
        seen_parts.add(part_key)
        for child in part.element.iterchildren():
            if child.tag == qn("w:p"):
                yield NativeParagraph(child, part)
            elif child.tag == qn("w:tbl"):
                yield NativeTable(child, part)


def iter_search_paragraphs(document: Any) -> Iterable[Any]:
    """Yield existing visible stories without creating missing header/footer parts."""
    yield from document.paragraphs
    for table in document.tables:
        yield from iter_table_paragraphs(table)

    for block in _iter_existing_story_blocks(document):
        name = type(block).__name__.lower()
        if "paragraph" in name:
            yield block
        elif "table" in name:
            yield from iter_table_paragraphs(block)


def iter_table_tree(table: Any) -> Iterable[Any]:
    """Yield one table and recursively nested tables exactly once per cell."""
    yield table
    seen: set[Any] = set()
    for row in table.rows:
        for cell in row.cells:
            key = cell._tc
            if key in seen:
                continue
            seen.add(key)
            for nested in cell.tables:
                yield from iter_table_tree(nested)


def iter_search_tables(document: Any) -> Iterable[Any]:
    """Yield body and existing header/footer tables, including nested tables."""
    for table in document.tables:
        yield from iter_table_tree(table)
    for block in _iter_existing_story_blocks(document):
        if "table" in type(block).__name__.lower():
            yield from iter_table_tree(block)


__all__ = ["iter_search_paragraphs", "iter_search_tables", "iter_table_tree"]
