"""Release layout guarantees; always offline and safe in public CI."""
from pathlib import Path
import re

from pywpdoc import Document

ROOT = Path(__file__).resolve().parents[2]


def test_version_single_source_and_docs_claim():
    cfg = (ROOT / 'pyproject.toml').read_text(encoding='utf8')
    assert re.search(r'^name\s*=\s*"pywpdoc"', cfg, re.M)
    assert re.search(r'^version\s*=\s*"0\.44\.0rc1"', cfg, re.M)
    assert re.search(r'^requires-python\s*=\s*">=3\.10"', cfg, re.M)
    assert '0.44.0rc1' in (ROOT / 'CHANGELOG.md').read_text(encoding='utf8')


def test_single_package_engine_and_no_legacy_module():
    assert (ROOT / 'src/pywpdoc/_engine/data/default.hwpx').is_file()
    assert not (ROOT / 'src/python_hwpx_next').exists()
    from pywpdoc._engine import Document as backend_document
    from pywpdoc._engine.core.errors import DocumentUnsupportedError
    from pywpdoc._engine.hwpx.table import Table as HwpxTable
    from pywpdoc._engine.docx.table import Table as DocxTable
    assert backend_document and DocumentUnsupportedError and HwpxTable and DocxTable
    metadata = (ROOT / 'pyproject.toml').read_text(encoding='utf8')
    assert 'include = ["pywpdoc*"]' in metadata
    assert 'python_hwpx_next' not in metadata


def test_readme_contains_real_asset_provenance_and_no_fictitious_badge():
    readme = (ROOT / 'README.md').read_text(encoding='utf8')
    assert 'One Python API. Two document formats.' in readme
    assert 'docs/assets/readme/docx-hwpx-contract-comparison.png' in readme
    assert 'github.com/rydolabs/PyWPDoc' in readme
    assert 'badge.svg' not in readme
    assert (ROOT / 'docs/assets/readme/PROVENANCE.md').is_file()


def test_workflows_separate_ci_from_oidc_release_publish():
    ci = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf8')
    publish = (ROOT / '.github/workflows/publish.yml').read_text(encoding='utf8')
    assert 'name: PyWPDoc CI' in ci
    assert 'contents: read' in ci
    assert 'workflow_dispatch:' in publish
    assert 'name: pypi' in publish
    assert 'id-token: write' in publish
    assert 'pypa/gh-action-pypi-publish@release/v1' in publish
