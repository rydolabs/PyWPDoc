"""v0.43.0 checkpoint: integration contracts across existing and new features.

No production code changes.  Native HWP acceptance/rejection cases below are
read-only checks of the already recorded Windows/Hancom 2020 outputs.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

import pytest
from lxml import etree

from pywpdoc import Document, DocumentUnsupportedError, DocumentValueError


ROOT = Path(__file__).resolve().parents[1]


def _parts(path):
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        return {n: hashlib.sha256(archive.read(n)).hexdigest() for n in archive.namelist()}


@pytest.mark.parametrize('fmt', ['docx', 'hwpx'])
def test_full_pipeline_template_preview_literal_regex_compare_roundtrip(fmt, tmp_path):
    doc = Document.new(fmt)
    p = doc.add_paragraph('고객: {{customer}}; CODE-123; 2026-10-13')
    tbl = doc.add_table(1, 2)
    tbl.cell(0, 0).text = '항목'
    tbl.cell(0, 1).text = '{{item}}'
    data = {'customer': '김철수', 'item': '노트'}
    input_path = tmp_path / ('template.' + fmt)
    doc.save(input_path)
    original = _parts(input_path)
    check = doc.check_template(data)
    assert check.ok and check.tag_count == 2
    assert doc.preview_replace('CODE', 'REF').count == 1
    assert len(doc.find_regex(r'\d{4}-\d\d-\d\d')) == 1
    assert json.loads(doc.preview_replace('CODE', 'REF').to_json())['count'] == 1
    preflight_path = tmp_path / ('preflight.' + fmt)
    doc.save(preflight_path)
    assert _parts(preflight_path) == original, 'read-only methods mutated package parts'

    assert doc.render_template(data) == 2
    rendered = tmp_path / ('rendered.' + fmt)
    doc.save(rendered)
    assert tbl.cell(0, 1).text == '노트'
    assert '김철수' in p.text
    predicted = doc.preview_replace('CODE-', 'REF-')
    assert predicted.count == 1
    assert doc.replace_text('CODE-', 'REF-') == predicted.count
    assert doc.replace_regex(r'(\d{4})-(\d\d)-(\d\d)', r'\1.\2.\3') == 1
    final = tmp_path / ('final.' + fmt)
    doc.save(final)
    loaded = Document.open(final)
    assert '김철수' in loaded.paragraphs[0].text
    assert 'REF-123' in loaded.paragraphs[0].text
    assert '2026.10.13' in loaded.paragraphs[0].text
    assert loaded.tables[0].cell(0, 1).text == '노트'
    assert not loaded.check_template({}).issues
    assert len(loaded.find_regex(r'REF-\d+')) == 1

    old = Document.open(rendered)
    review = old.compare(loaded, author='Integration QA', date='2026-10-13T09:00:00Z')
    reviewed_path = tmp_path / ('tracked.' + fmt)
    review.save(reviewed_path)
    assert _parts(reviewed_path)
    with zipfile.ZipFile(reviewed_path) as archive:
        section = archive.read('word/document.xml' if fmt == 'docx' else 'Contents/section0.xml')
    if fmt == 'docx':
        assert b'<w:ins' in section and b'<w:del' in section
    else:
        assert b'insertBegin' in section and b'deleteBegin' in section
    assert '2026-10-13' in old.paragraphs[0].text
    assert '2026.10.13' in loaded.paragraphs[0].text


@pytest.mark.parametrize('fmt', ['docx', 'hwpx'])
def test_table_row_template_then_preview_regex_no_cross_format_regression(fmt, tmp_path):
    doc = Document.new(fmt)
    tbl = doc.add_table(2, 3)
    tbl.cell(0, 0).text = '이름'
    tbl.cell(0, 1).text = '개수'
    tbl.cell(0, 2).text = '코드'
    tbl.cell(1, 0).text = '{{#items}}{{name}}'
    tbl.cell(1, 1).text = '{{qty}}'
    tbl.cell(1, 2).text = '{{code}}{{/items}}'
    payload = {'items': [
        {'name': '가', 'qty': 2, 'code': 'ITEM-12'},
        {'name': '나', 'qty': 3, 'code': 'ITEM-34'},
    ]}
    assert doc.check_template(payload, sections=True, table_rows=True).ok
    before = tmp_path / ('before.' + fmt)
    doc.save(before)
    assert doc.render_template(payload, sections=True, table_rows=True) > 0
    assert len(tbl.rows) == 3
    assert [r.cells[2].text for r in tbl.rows] == ['코드', 'ITEM-12', 'ITEM-34']
    assert doc.preview_replace('ITEM-', 'SKU-').count == 2
    assert doc.replace_text('ITEM-', 'SKU-') == 2
    assert doc.replace_regex(r'SKU-(\d\d)', r'SKU-20\1') == 2
    after = tmp_path / ('after.' + fmt)
    doc.save(after)
    again = Document.open(after)
    assert [r.cells[2].text for r in again.tables[0].rows] == ['코드', 'SKU-2012', 'SKU-2034']
    assert again.check_template(payload, sections=True, table_rows=True).ok
    assert len(again.find_regex(r'SKU-20\d\d')) == 2


@pytest.mark.parametrize('fmt', ['docx', 'hwpx'])
def test_bad_regex_atomicity_with_other_features_unaffected(fmt, tmp_path):
    doc = Document.new(fmt)
    doc.add_paragraph('A1 B2 {{username}}')
    doc.add_paragraph('C3 D4')
    before = tmp_path / ('before.' + fmt)
    doc.save(before)
    original = _parts(before)
    with pytest.raises(DocumentValueError):
        doc.replace_regex(r'([A-Z]\d)', r'\2')  # bad backreference
    with pytest.raises(DocumentUnsupportedError):
        doc.replace_regex(r'(?=D4)|[A-Z]\d', 'x')  # zero-width on later paragraph
    with pytest.raises(DocumentValueError):
        doc.replace_regex('[', 'x')
    after = tmp_path / ('after.' + fmt)
    doc.save(after)
    assert _parts(after) == original
    assert doc.check_template({'username':'박'}).ok
    assert doc.preview_replace('A1','X').count == 1
    assert doc.render_template({'username':'박'}) == 1
    assert doc.replace_regex(r'[A-Z]\d', 'X') == 4


@pytest.mark.parametrize('fmt', ['docx', 'hwpx'])
def test_table_structure_compare_fails_closed_while_sibling_apis_remain_usable(fmt, tmp_path):
    old, new = Document.new(fmt), Document.new(fmt)
    old.add_table(1, 1).cell(0, 0).text = 'A'
    new.add_table(2, 1).cell(0, 0).text = 'A'
    new.tables[0].cell(1, 0).text = 'B'
    oldfile, newfile = (tmp_path / ('old.' + fmt)), (tmp_path / ('new.' + fmt))
    old.save(oldfile)
    new.save(newfile)
    orig_old, orig_new = _parts(oldfile), _parts(newfile)
    if fmt == 'hwpx':
        with pytest.raises(DocumentUnsupportedError):
            old.compare(new)
    else:
        # DOCX can represent whole-table-row revisions; keep this distinction.
        result = old.compare(new)
        result.save(tmp_path / 'docx_row_review.docx')
    assert old.preview_replace('A', 'X').count == 1
    assert new.preview_replace('B', 'Y').count == 1
    assert old.find_regex('A') and new.find_regex('B')
    old.save(oldfile)
    new.save(newfile)
    assert _parts(oldfile) == orig_old and _parts(newfile) == orig_new


def test_native_tracked_file_read_only_new_apis_preserve_package_parts(tmp_path):
    src = ROOT / 'tests/fixtures/historical/qa_native_accept_reject_v0400' / 'SOURCE_TRACKED_V22.hwpx'
    doc = Document.open(src)
    # Compare with a plain reopen/save baseline to discount the pre-existing
    # HWPX content.hpf serialization normalization on any saved native file.
    baseline = tmp_path / 'baseline_untouched.hwpx'
    Document.open(src).save(baseline)
    prior = _parts(baseline)
    assert doc.check_template({}).ok
    assert len(doc.find_regex(r'[A-Z]{2,4}')) > 0
    assert doc.preview_replace('NEW', 'NEW-REVISED').count > 0
    saved = tmp_path / 'tracked_untouched.hwpx'
    doc.save(saved)
    assert _parts(saved) == prior
    with zipfile.ZipFile(saved) as archive:
        assert b'insertBegin' in archive.read('Contents/section0.xml')


@pytest.mark.parametrize('name', ['ACCEPT_ALL_NATIVE.hwpx', 'REJECT_ALL_NATIVE.hwpx'])
def test_native_approved_rejected_snapshots_remain_readable_and_unchanged(name, tmp_path):
    # Reuse the actual prior Hancom Windows result bundled within the project.
    # Saving an HWPX can normalize content.hpf independently of these methods.
    zip_path = (ROOT / 'tests/fixtures/historical/qa_native_accept_reject_v0400'
                / 'native_verified_2026_10_13' / 'HWP_REVIEW_RESULTS_V2_NATIVE.zip')
    if not zip_path.exists():
        pytest.skip('Historical native result archive intentionally excluded from public repository; local-only fixture')
    with zipfile.ZipFile(zip_path) as archive:
        fixture = tmp_path / name
        fixture.write_bytes(archive.read(name))
    before = tmp_path / ('baseline_' + name)
    Document.open(fixture).save(before)
    doc = Document.open(fixture)
    assert doc.check_template({}).ok
    doc.find_regex(r'\w+')
    doc.preview_replace('NEW', 'UPDATED')
    after = tmp_path / ('after_' + name)
    doc.save(after)
    assert _parts(before) == _parts(after)
    with zipfile.ZipFile(after) as archive:
        section = etree.fromstring(archive.read('Contents/section0.xml'))
    assert not any(etree.QName(item).localname in ('insertBegin', 'deleteBegin') for item in section.iter())
