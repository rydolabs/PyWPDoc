"""Issue regression: Word may normalize a one-row full merged table grid.

All documents are authored through PyWPDoc Common API, tested for DOCX and HWPX.
The Windows Word roundtrip is a separate true-native gate, never faked in CI.
"""
from __future__ import annotations

import pytest
from pywpdoc import Document
from tests.generators.business_docs.merge_grid import (
    CASES, build_case, check_common_api, document_xml,
    inspect_docx, assert_word_merge_semantics,
)


@pytest.mark.regression
@pytest.mark.common_api
@pytest.mark.parametrize('case', CASES, ids=lambda c:c.key)
@pytest.mark.parametrize('fmt', ['docx','hwpx'])
def test_merge_survives_common_api_save_reopen(tmp_path, fmt, case):
    path = tmp_path / f'{case.key}.{fmt}'
    build_case(case,fmt).save(path)
    result = check_common_api(path, case)
    assert result['rows'] == case.rows
    assert result['columns'] == case.cols


@pytest.mark.regression
@pytest.mark.common_api
@pytest.mark.parametrize('case', CASES, ids=lambda c:c.key)
@pytest.mark.parametrize('fmt', ['docx','hwpx'])
def test_merge_survives_second_common_api_save(tmp_path, fmt, case):
    first, second = tmp_path / f'first.{fmt}', tmp_path / f'second.{fmt}'
    build_case(case,fmt).save(first)
    Document.open(first).save(second)
    check_common_api(second, case)
    # DOCX should preserve its topological logical table grid on a PyWPDoc-only roundtrip.
    if fmt == 'docx':
        assert inspect_docx(first)['tables'] == inspect_docx(second)['tables']


@pytest.mark.regression
@pytest.mark.common_api
@pytest.mark.parametrize('case', CASES, ids=lambda c:c.key)
@pytest.mark.parametrize('fmt', ['docx','hwpx'])
def test_merge_remains_editable_after_reopen(tmp_path, fmt, case):
    first, second = tmp_path / f'edit.{fmt}', tmp_path / f'edited.{fmt}'
    build_case(case,fmt).save(first)
    document = Document.open(first)
    table = document.tables[0]
    if case.region:
        r,c,*_ = case.region
    else:
        r,c = 0,0
    old = table.cell(r,c).text
    table.cell(r,c).text = old + '::POST-EDIT'
    document.save(second)
    reopened = Document.open(second)
    assert reopened.tables[0].cell(r,c).text == old + '::POST-EDIT'
    assert len(reopened.tables[0].rows) == case.rows
    assert len(reopened.tables[0].columns) == case.cols


@pytest.mark.regression
@pytest.mark.parametrize('case', CASES, ids=lambda c:c.key)
def test_docx_merge_has_explicit_physical_topology(tmp_path, case):
    path = tmp_path / 'topology.docx'
    build_case(case,'docx').save(path)
    snapshot = inspect_docx(path)
    assert len(snapshot['tables']) == 1
    table = snapshot['tables'][0]
    assert table['grid_columns'] == case.cols
    assert len(table['rows']) == case.rows
    if case.region:
        r0,c0,r1,c1 = case.region
        assert len(table['rows'][r0]) < case.cols if c1 > c0 else True
        if r1 > r0:
            assert any(cell['vmerge'] == 'restart' for cell in table['rows'][r0])
            assert any(cell['vmerge'] == 'continue' for cell in table['rows'][r1])
        if c1 > c0:
            assert any(cell['span'] == c1-c0+1 for cell in table['rows'][r0])


@pytest.mark.regression
@pytest.mark.parametrize('case', CASES, ids=lambda c:c.key)
def test_word_semantic_validator_accepts_identical_docx(tmp_path, case):
    path = tmp_path / 'same.docx'
    build_case(case, 'docx').save(path)
    result = assert_word_merge_semantics(path, path)
    assert result['single_row_grid_normalizations'] == []


@pytest.mark.regression
def test_word_semantic_validator_detects_lost_text(tmp_path):
    from zipfile import ZipFile, ZIP_DEFLATED
    case = CASES[0]
    a, b = tmp_path/'original.docx',tmp_path/'altered.docx'
    build_case(case,'docx').save(a)
    with ZipFile(a) as original, ZipFile(b,'w',compression=ZIP_DEFLATED) as modified:
        for entry in original.infolist():
            data = original.read(entry.filename)
            if entry.filename == 'word/document.xml':
                data = data.replace(b'MERGED-REGION',b'SILENTLY-LOST')
            modified.writestr(entry, data)
    with pytest.raises(AssertionError,match='body text'):
        assert_word_merge_semantics(a,b)


@pytest.mark.regression
def test_word_semantic_validator_rejects_erased_multirow_merge(tmp_path):
    """Preserved text does NOT excuse a broken two-row merger."""
    from zipfile import ZipFile, ZIP_DEFLATED
    from lxml import etree
    from tests.generators.business_docs.merge_grid import W
    case = next(c for c in CASES if c.key == 'vertical_two')
    a,b = tmp_path/'original.docx',tmp_path/'broken.docx'
    build_case(case,'docx').save(a)
    with ZipFile(a) as original, ZipFile(b,'w',compression=ZIP_DEFLATED) as modified:
        for entry in original.infolist():
            data = original.read(entry.filename)
            if entry.filename == 'word/document.xml':
                root = etree.fromstring(data)
                vmerge = root.find('.//'+W+'vMerge')
                assert vmerge is not None
                vmerge.getparent().remove(vmerge)
                data = etree.tostring(root, encoding='UTF-8', xml_declaration=True)
            modified.writestr(entry,data)
    with pytest.raises(AssertionError,match='merged-cell topology'):
        assert_word_merge_semantics(a,b)


@pytest.mark.common_api
@pytest.mark.regression
@pytest.mark.parametrize('fmt',['docx','hwpx'])
@pytest.mark.parametrize('align',['CENTER','BOTTOM'])
def test_merged_cell_vertical_alignment_retained(tmp_path, fmt, align):
    from pywpdoc import Document, WD_ALIGN_VERTICAL
    case = next(x for x in CASES if x.key == 'rectangle_2x2')
    document = build_case(case,fmt)
    region = document.tables[0].cell(1,1)
    region.vertical_alignment = getattr(WD_ALIGN_VERTICAL,align)
    path = tmp_path/f'align.{fmt}'
    document.save(path)
    reopened = Document.open(path)
    assert reopened.tables[0].cell(1,1).vertical_alignment == getattr(WD_ALIGN_VERTICAL,align)
    assert reopened.tables[0].cell(2,2).vertical_alignment == getattr(WD_ALIGN_VERTICAL,align)


@pytest.mark.common_api
@pytest.mark.regression
@pytest.mark.parametrize('fmt',['docx','hwpx'])
def test_table_grid_style_roundtrip_after_merge(tmp_path, fmt):
    case = next(x for x in CASES if x.key == 'horizontal_partial')
    doc = build_case(case,fmt)
    source, output = tmp_path/f'source.{fmt}',tmp_path/f'output.{fmt}'
    doc.save(source)
    Document.open(source).save(output)
    check_common_api(output,case)
    if fmt == 'docx':
        from tests.generators.business_docs.merge_grid import W
        tblpr = document_xml(output).find('.//'+W+'tblPr')
        assert tblpr is not None
        style = tblpr.find(W+'tblStyle')
        assert style is not None and style.get(W+'val') == 'TableGrid'
