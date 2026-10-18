"""Data-preservation gate for a hypothetical Word re-save of business DOCX."""
from __future__ import annotations
from zipfile import ZipFile, ZIP_DEFLATED

import pytest
from pywpdoc import Document
from tests.generators.business_docs.scenarios import SCENARIOS, build_document
from tests.generators.business_docs.preservation import assert_docx_preserved


@pytest.mark.regression
@pytest.mark.parametrize('key', ['01_contract', '11_purchase_order', '23_complex_tables', '24_long_form'])
def test_docx_resave_roundtrip_preserves_text_and_media(tmp_path, key):
    scenario = next(s for s in SCENARIOS if s.key == key)
    source, output = tmp_path / 'source.docx', tmp_path / 'output.docx'
    doc, _ = build_document(scenario, 'docx')
    doc.save(source)
    Document.open(source).save(output)
    assert assert_docx_preserved(source, output)['body_text_equal']


@pytest.mark.regression
def test_docx_preservation_gate_detects_silent_text_loss(tmp_path):
    a = tmp_path / 'a.docx'
    b = tmp_path / 'b.docx'
    first = Document.new('docx')
    first.add_paragraph('KEEP THIS')
    first.save(a)
    second = Document.new('docx')
    second.add_paragraph('LOST THIS')
    second.save(b)
    with pytest.raises(AssertionError, match='body text'):
        assert_docx_preserved(a, b)
