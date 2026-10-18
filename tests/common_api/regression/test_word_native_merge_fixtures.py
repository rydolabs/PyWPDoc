"""Real user-supplied *synthetic* before/after Word COM resave pairs.

No installed Word is required to audit these archived known-good examples.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import pytest
from tests.generators.business_docs.merge_grid import assert_word_merge_semantics, inspect_docx

FIXTURE_DIR = Path(__file__).resolve().parents[2]/'fixtures'/'word_merge_regression'


@pytest.mark.regression
@pytest.mark.parametrize('key', ('01_contract','11_purchase_order','23_complex_tables'))
def test_observed_word_single_row_grid_normalization_is_semantically_valid(key):
    info = json.loads((FIXTURE_DIR/'manifest.json').read_text(encoding='utf-8'))[key]
    paths = {}
    for role in ('source','word_saved'):
        paths[role] = FIXTURE_DIR/info[role]['file']
        assert hashlib.sha256(paths[role].read_bytes()).hexdigest() == info[role]['sha256']
    result = assert_word_merge_semantics(paths['source'], paths['word_saved'])
    assert len(result['single_row_grid_normalizations']) == 1
    assert result['single_row_grid_normalizations'][0]['before_grid'] == 2
    assert result['single_row_grid_normalizations'][0]['after_grid'] == 1


@pytest.mark.regression
@pytest.mark.parametrize('key', ('01_contract','11_purchase_order','23_complex_tables'))
def test_native_resaved_fixtures_are_structurally_reopenable(key):
    from pywpdoc import Document
    info = json.loads((FIXTURE_DIR/'manifest.json').read_text(encoding='utf-8'))[key]
    path = FIXTURE_DIR/info['word_saved']['file']
    doc = Document.open(path)
    assert len(doc.tables) == {'01_contract':2,'11_purchase_order':2,'23_complex_tables':4}[key]
    assert any('MERGE-MARK' in t.cell(0,0).text for t in doc.tables)
