"""24 realistic document intents x two Common API formats; no native authoring shortcuts."""
from __future__ import annotations
import pytest
from pywpdoc import Document
from tests.generators.business_docs.scenarios import SCENARIOS, build_document, open_and_check
from tests.generators.business_docs.audit import audit_archive


@pytest.fixture(scope='module', params=[(s, f) for s in SCENARIOS for f in ('docx', 'hwpx')],
                ids=[f'{s.key}-{f}' for s in SCENARIOS for f in ('docx', 'hwpx')])
def saved_document(request, tmp_path_factory):
    scenario, fmt = request.param
    out = tmp_path_factory.mktemp('biz-corpus') / f'{scenario.key}.{fmt}'
    doc, expected = build_document(scenario, fmt)
    doc.save(out)
    return out, expected


@pytest.mark.common_api
def test_business_document_roundtrip_preserves_paragraphs_tables_and_metadata(saved_document):
    path, expected = saved_document
    actual = open_and_check(path, expected)
    if expected['id'] == '24_long_form':
        assert actual['paragraphs'] >= 1000
        assert actual['tables'] >= 13


@pytest.mark.common_api
def test_business_document_package_has_valid_xml_crc_and_image_payload(saved_document):
    path, expected = saved_document
    result = audit_archive(path, expect_image=expected['has_image'])
    assert result['members'] > 4
    assert result['parsed_xml'] >= 2


@pytest.mark.common_api
def test_business_document_resave_retains_content_without_modifying_original(saved_document, tmp_path):
    path, expected = saved_document
    before = path.read_bytes()
    edit = Document.open(path)
    edit.add_paragraph('QA-POST-EDIT-SENTINEL')
    out = tmp_path / ('resaved.' + expected['format'])
    edit.save(out)
    open_and_check(out, expected)
    assert 'QA-POST-EDIT-SENTINEL' in [p.text for p in Document.open(out).paragraphs]
    assert path.read_bytes() == before, 'editing document changed original input'
    audit_archive(out, expect_image=expected['has_image'])
