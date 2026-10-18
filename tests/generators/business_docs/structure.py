"""Cross-editor-safe DOCX table structure checks for the business corpus.

Independent top-level tables must be separated by a w:p in word/document.xml;
otherwise Microsoft Word can normalize contiguous w:tbl siblings into one table.
This is a *scenario authoring invariant*, not a promise that all DOCX from
arbitrary sources will have independent adjacent tables.
"""
from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def audit_docx_independent_tables(path: Path, *, expected_tables: int | None = None) -> dict:
    """Check top-level table count and paragraph separators between each pair.

    Does not count nested tables and does not weaken round-trip structure checks.
    """
    with ZipFile(path) as package:
        root = ET.fromstring(package.read('word/document.xml'))
    body = root.find(f'{W}body')
    if body is None:
        raise AssertionError('DOCX is missing w:body')
    children = list(body)
    indices = [i for i, child in enumerate(children) if child.tag == f'{W}tbl']
    between = [children[left + 1:right] for left, right in zip(indices, indices[1:])]
    without_separator = [i for i, blocks in enumerate(between)
                         if not any(block.tag == f'{W}p' for block in blocks)]
    stats = {'top_level_tables': len(indices), 'table_pairs': len(between),
             'separated_pairs': len(between) - len(without_separator),
             'missing_separators_at_pairs': without_separator}
    if expected_tables is not None:
        assert stats['top_level_tables'] == expected_tables, stats
    assert not without_separator, f'Adjacent independent DOCX tables lack a w:p separator: {stats}'
    return stats
