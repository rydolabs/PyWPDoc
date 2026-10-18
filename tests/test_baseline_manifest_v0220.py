from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from pywpdoc._engine.common import Document as BaselineDocument
from pywpdoc import Document as PyDocument

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "tests/baseline/v0215_manifest.json").read_text(encoding="utf-8"))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _zip_hashes(path: Path, selected: set[str] | None = None) -> dict[str, str]:
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        if selected is not None:
            names &= selected
        return {name: _sha(zf.read(name)) for name in sorted(names)}


def test_v0215_source_fixture_is_immutable() -> None:
    source = ROOT / MANIFEST["source_fixture"]
    assert _sha(source.read_bytes()) == MANIFEST["source_sha256"]
    assert _zip_hashes(source) == MANIFEST["hwpx_package_parts"]


def test_pywpdoc_hwpx_preserves_static_v0215_golden(tmp_path: Path) -> None:
    source = ROOT / MANIFEST["source_fixture"]
    out = tmp_path / "pywpdoc.hwpx"
    PyDocument.rebuild(source, format="hwpx", preserve_layout=True).save(out)
    assert _zip_hashes(out) == MANIFEST["hwpx_package_parts"]


def test_pywpdoc_docx_matches_static_v0215_selected_parts(tmp_path: Path) -> None:
    source = ROOT / MANIFEST["source_fixture"]
    out = tmp_path / "pywpdoc.docx"
    PyDocument.rebuild(source, format="docx", preserve_layout=True).save(out)
    selected = set(MANIFEST["docx_selected_parts"])
    assert _zip_hashes(out, selected) == MANIFEST["docx_selected_parts"]
