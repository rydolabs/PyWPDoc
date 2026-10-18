"""Windows QA evidence packaging tests; no installed Word/Hancom needed."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
from zipfile import ZipFile
import pytest

from tests.generators.business_docs.generate import generate
from tests.generators.business_docs import windows_review


@pytest.mark.regression
def test_windows_results_bundle_contains_exact_com_input_and_digests(tmp_path, monkeypatch):
    generated = tmp_path / 'generated'
    output = tmp_path / 'native'
    info = generate(generated, formats=('docx',), only={'01_contract'})
    assert info['passed'] == 1

    def fake_native_worker(cmd, **_kwargs):
        source = Path(cmd[cmd.index('--source') + 1])
        target = Path(cmd[cmd.index('--out') + 1])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return SimpleNamespace(returncode=0, stdout=json.dumps({'status': 'PASS', 'open_save': 'PASS'}), stderr='')

    monkeypatch.setattr(windows_review.subprocess, 'run', fake_native_worker)
    monkeypatch.setattr(sys, 'argv', ['windows_review', '--generated', str(generated), '--out', str(output), '--only', '01_contract'])
    assert windows_review.main() == 0

    manifest = json.loads((output / 'windows_results.json').read_text(encoding='utf-8'))
    case = manifest['cases'][0]
    src = generated / '01_contract.docx'
    original = src.read_bytes()
    assert case['source_hash_verified'] is True
    assert case['source_sha256'] == hashlib.sha256(original).hexdigest()
    assert case['resaved_sha256'] == case['source_sha256']
    with ZipFile(output / 'BUSINESS_NATIVE_QA_RESULTS.zip') as archive:
        assert 'generated_inputs/manifest.json' in archive.namelist()
        assert archive.read('generated_inputs/01_contract.docx') == original
        assert json.loads(archive.read('generated_inputs/manifest.json'))['passed'] == 1
        assert 'resaved/01_contract.docx' in archive.namelist()


@pytest.mark.regression
def test_windows_review_refuses_empty_selected_scenarios(tmp_path, monkeypatch):
    generated = tmp_path / 'generated'
    generate(generated, formats=('docx',), only={'01_contract'})
    monkeypatch.setattr(sys, 'argv', ['windows_review', '--generated', str(generated),
                                      '--out', str(tmp_path / 'native'), '--only', 'not-present'])
    with pytest.raises(SystemExit, match='No generated PASS cases'):
        windows_review.main()
