"""Regression for 2026-10-15 Windows Word re-save table coalescing.

Observed before fix:
  01_contract: 2 -> 1; 11_purchase_order: 2 -> 1;
  23_complex_tables: 4 -> 1; 24_long_form: 13 -> 2.
Separate top-level tables by a w:p, preserving their identity in Word.
The actual Windows COM gate is still required to certify the fix.
"""
from __future__ import annotations
import pytest
from pywpdoc import Document
from tests.generators.business_docs.scenarios import SCENARIOS, build_document, open_and_check
from tests.generators.business_docs.structure import audit_docx_independent_tables

AFFECTED = ('01_contract', '11_purchase_order', '23_complex_tables', '24_long_form')
SCENARIO_BY_KEY = {s.key: s for s in SCENARIOS}


@pytest.mark.regression
@pytest.mark.parametrize('key', AFFECTED)
def test_independent_docx_tables_have_ooxml_paragraph_separators(tmp_path, key):
    scenario = SCENARIO_BY_KEY[key]
    doc, expected = build_document(scenario, 'docx')
    path = tmp_path / f'{key}.docx'
    doc.save(path)
    data = audit_docx_independent_tables(path, expected_tables=expected['tables'])
    assert data['separated_pairs'] == expected['tables'] - 1
    assert data['missing_separators_at_pairs'] == []
    open_and_check(path, expected)


@pytest.mark.regression
@pytest.mark.parametrize('key', AFFECTED)
def test_independent_docx_tables_remain_separate_after_pywpdoc_resave(tmp_path, key):
    scenario = SCENARIO_BY_KEY[key]
    doc, expected = build_document(scenario, 'docx')
    source = tmp_path / f'{key}.docx'
    target = tmp_path / f'{key}.resaved.docx'
    doc.save(source)
    Document.open(source).save(target)
    open_and_check(target, expected)
    stats = audit_docx_independent_tables(target, expected_tables=expected['tables'])
    assert stats['separated_pairs'] == expected['tables'] - 1


@pytest.mark.regression
@pytest.mark.parametrize('key', AFFECTED)
def test_original_hwpx_business_scenarios_still_roundtrip(tmp_path, key):
    scenario = SCENARIO_BY_KEY[key]
    doc, expected = build_document(scenario, 'hwpx')
    path = tmp_path / f'{key}.hwpx'
    doc.save(path)
    open_and_check(path, expected)


@pytest.mark.regression
def test_adjacent_independent_tables_without_separator_are_detected(tmp_path):
    doc = Document.new('docx')
    doc.add_table(1, 1).cell(0, 0).text = 'TABLE A'
    doc.add_table(1, 1).cell(0, 0).text = 'TABLE B'
    path = tmp_path / 'unsafe_adjacent.docx'
    doc.save(path)
    with pytest.raises(AssertionError, match='lack a w:p separator'):
        audit_docx_independent_tables(path, expected_tables=2)


@pytest.mark.regression
def test_blank_paragraph_is_sufficient_separator_for_docx(tmp_path):
    doc = Document.new('docx')
    doc.add_table(1, 1).cell(0, 0).text = 'TABLE A'
    doc.add_paragraph('')
    doc.add_table(1, 1).cell(0, 0).text = 'TABLE B'
    path = tmp_path / 'safe_separated.docx'
    doc.save(path)
    assert audit_docx_independent_tables(path, expected_tables=2)['separated_pairs'] == 1
