"""Release layout guarantees; always offline and safe in public CI."""
from pathlib import Path
import re

from pywpdoc import Document

ROOT = Path(__file__).resolve().parents[2]


def test_version_single_source_and_docs_claim():
    cfg = (ROOT / 'pyproject.toml').read_text(encoding='utf8')
    assert re.search(r'^name\s*=\s*"pywpdoc"', cfg, re.M)
    assert re.search(r'^version\s*=\s*"0\.44\.0"', cfg, re.M)
    assert re.search(r'^requires-python\s*=\s*">=3\.10"', cfg, re.M)
    assert '## 0.44.0 ' in (ROOT / 'CHANGELOG.md').read_text(encoding='utf8')


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
    # The default installer now covers both editable formats.
    assert 'dependencies = ["lxml>=4.9", "python-docx>=1.2,<2"]' in metadata
    assert 'unified = ["python-docx>=1.2,<2"]' in metadata


def test_readme_contains_real_asset_provenance_and_no_fictitious_badge():
    readme = (ROOT / 'README.md').read_text(encoding='utf8')
    # The first screen may evolve; enforce the actual product promise, not a
    # frozen advertising headline.
    assert 'Microsoft Word DOCX' in readme
    assert 'Hancom Hangul HWPX' in readme
    assert 'from pywpdoc import Document' in readme
    assert '**Version: 0.44.0.**' in readme
    assert 'docs/assets/readme/docx-hwpx-contract-comparison.png' in readme
    assert 'docs/assets/readme/contract-word.png' in readme
    assert 'docs/assets/readme/complex-tables-docx.png' in readme
    assert 'https://rydolabs.github.io/PyWPDoc/reference/document/' in readme
    assert 'pip install pywpdoc' in readme
    assert 'check_template(data)' in readme
    assert 'before.compare(after' in readme
    assert 'preview_replace(' in readme
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


def test_github_release_workflow_is_manual_sha_pinned_and_separate_from_pypi():
    """Creating a GitHub Release must never happen on a routine CI push."""
    release = (ROOT / '.github/workflows/release.yml').read_text(encoding='utf8')

    # Validate YAML structure when PyYAML is installed (e.g., docs CI).
    try:
        import yaml
    except ImportError:
        pass
    else:
        parsed = yaml.load(release, Loader=yaml.BaseLoader)
        assert parsed['on']['workflow_dispatch']['inputs']
        assert 'push' not in parsed['on']
        assert 'pull_request' not in parsed['on']
        assert 'release' not in parsed['on']

    assert 'on:\n  workflow_dispatch:' in release
    assert 'github.ref == \'refs/heads/main\'' in release
    assert 'release_tag:' in release
    assert 'expected_sha:' in release
    assert 'confirm_release:' in release
    assert '[[ "$CONFIRM_RELEASE" == PUBLISH ]]' in release
    assert 'gh api "repos/$REPO/git/ref/heads/main"' in release
    assert 'head_branch == "main"' in release
    assert 'conclusion == "success"' in release
    assert 'git ls-remote --tags origin' in release
    assert 'project["version"] == os.environ["RELEASE_TAG"][1:]' in release
    assert 'python -m twine check --strict dist/*' in release
    assert 'wheel_smoke.py' in release
    assert 'sha256sum --check SHA256SUMS' in release
    assert 'gh release create' in release
    assert '--prerelease --latest=false' in release
    assert 'name: github-release' in release
    assert 'contents: write' in release
    assert 'pypa/gh-action-pypi-publish' not in release
    assert 'secrets.PYPI_API_TOKEN' not in release
