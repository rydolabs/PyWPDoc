"""Common-API authored merged-cell corpus and semantic Word roundtrip checks.

A single physical cell spanning a one-row table can legitimately be rewritten by
Word from 2-column gridSpan=2 to a 1-column grid with no gridSpan. This exception
is deliberately narrow: multi-row spans, cell loss, text loss or changed table
boundaries must fail. No backend-native authoring is used.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile
from lxml import etree
from pywpdoc import Document

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


@dataclass(frozen=True)
class MergeCase:
    key: str
    rows: int
    cols: int
    region: tuple[int, int, int, int] | None


CASES = (
    MergeCase('single_row_full', 1, 2, (0, 0, 0, 1)),
    MergeCase('horizontal_partial', 2, 3, (0, 1, 0, 2)),
    MergeCase('horizontal_three', 2, 4, (0, 1, 0, 3)),
    MergeCase('vertical_two', 3, 3, (0, 0, 1, 0)),
    MergeCase('vertical_three', 4, 2, (0, 1, 2, 1)),
    MergeCase('rectangle_2x2', 3, 3, (1, 1, 2, 2)),
    MergeCase('rectangle_2x3', 4, 4, (1, 1, 2, 3)),
    MergeCase('unmerged_control', 2, 3, None),
)
CASES_BY_KEY = {c.key: c for c in CASES}


def marker(case: MergeCase) -> str:
    return f'MERGED-REGION::{case.key}::한글-A1-123'


def build_case(case: MergeCase, fmt: str):
    """Use only the public PyWPDoc Common API (never native python-docx editing)."""
    document = Document.new(fmt)
    document.add_paragraph('MERGE-GRID-START::' + case.key)
    table = document.add_table(case.rows, case.cols, style='Table Grid')
    rgn = case.region
    for r in range(case.rows):
        for c in range(case.cols):
            if rgn and rgn[0] <= r <= rgn[2] and rgn[1] <= c <= rgn[3]:
                continue
            table.cell(r, c).text = f'CELL::{case.key}::{r},{c}'
    if rgn:
        table.cell(rgn[0], rgn[1]).merge(table.cell(rgn[2], rgn[3])).text = marker(case)
    document.add_paragraph('MERGE-GRID-END::' + case.key)
    return document


def check_common_api(path: Path, case: MergeCase) -> dict:
    doc = Document.open(path)
    assert len(doc.tables) == 1, f'changed top-level table count: {path}'
    table = doc.tables[0]
    assert len(table.rows) == case.rows, (case, len(table.rows))
    # DOCX one-row fully merged tables may have a single column after Word save.
    collapsed = bool(doc.format == 'docx' and case.key == 'single_row_full' and len(table.columns) == 1)
    assert len(table.columns) == (1 if collapsed else case.cols), (case, len(table.columns))
    for r in range(case.rows):
        for c in range(case.cols):
            if collapsed and c > 0:
                continue
            region = case.region
            expected = (marker(case) if region and region[0] <= r <= region[2] and
                        region[1] <= c <= region[3] else f'CELL::{case.key}::{r},{c}')
            assert table.cell(r, c).text == expected, (case.key, r, c, table.cell(r,c).text, expected)
    return {'rows':case.rows,'columns':len(table.columns),'normalized_single_row':collapsed}


def document_xml(path: Path):
    with ZipFile(path) as package:
        return etree.fromstring(package.read('word/document.xml'))


def _body_text(xml):
    # Raw w:t sequence is intentionally examined, including text within tables.
    return ''.join(n.text or '' for n in xml.iter(W+'t'))


def _table_data(xml):
    body = xml.find(W+'body')
    assert body is not None
    tables = []
    for table in body.findall(W+'tbl'):
        grid = table.find(W+'tblGrid')
        grid_columns = len(grid.findall(W+'gridCol')) if grid is not None else 0
        rows = []
        for row in table.findall(W+'tr'):
            cells = []
            for cell in row.findall(W+'tc'):
                pr = cell.find(W+'tcPr')
                span = pr.find(W+'gridSpan') if pr is not None else None
                vertical = pr.find(W+'vMerge') if pr is not None else None
                cells.append({'text': ''.join(x.text or '' for x in cell.iter(W+'t')),
                              'span':int(span.get(W+'val','1')) if span is not None else 1,
                              'vmerge':(vertical.get(W+'val','continue') if vertical is not None else None)})
            rows.append(cells)
        tables.append({'grid_columns':grid_columns,'rows':rows})
    return tables


def inspect_docx(path: Path) -> dict:
    xml = document_xml(path)
    return {'text':_body_text(xml),'tables':_table_data(xml)}


def _is_single_row_total_merge(table):
    # A physically one-cell, one-row table has one visible cell whether the grid
    # has 1 col or multiple cols and the sole cell spans them.
    return (len(table['rows']) == 1 and len(table['rows'][0]) == 1 and
            table['grid_columns'] > 0 and
            table['rows'][0][0]['span'] == table['grid_columns'] and
            table['rows'][0][0]['vmerge'] is None)


def assert_word_merge_semantics(source: Path, resaved: Path) -> dict:
    """Compare same-run original vs Word saved document, allowing only proved normalization.

    Verify package, all body text and physical cells. Do NOT mistake any arbitrary
    collapsed table for benign grid canonicalization. A multirow lost merge fails.
    """
    before, after = inspect_docx(source), inspect_docx(resaved)
    assert before['text'] == after['text'], 'Word resave changed body text'
    orig, new = before['tables'], after['tables']
    assert len(orig) == len(new), 'Word resave changed independent table count'
    normalized = []
    for i, (a, b) in enumerate(zip(orig, new)):
        if a == b:
            continue
        # Widened/narrowed column widths are allowed because these signatures
        # deliberately omit twip widths. Other differences must be justified.
        if (a['grid_columns'] != b['grid_columns'] or
            len(a['rows']) != len(b['rows']) or a['rows'] != b['rows']):
            if (_is_single_row_total_merge(a) and _is_single_row_total_merge(b)
                    and a['rows'][0][0]['text'] == b['rows'][0][0]['text']):
                normalized.append({'table_index':i,'before_grid':a['grid_columns'],
                                   'after_grid':b['grid_columns']})
                continue
            raise AssertionError(f'Word resave modified nontrivial merged-cell topology at table {i}')
    return {'table_count':len(orig),'body_text_equal':True,
            'single_row_grid_normalizations':normalized}
