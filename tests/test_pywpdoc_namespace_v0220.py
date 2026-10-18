from __future__ import annotations

import hashlib
import importlib
import zipfile
from pathlib import Path

import pytest

from pywpdoc import Document as PyDocument
from pywpdoc.hwpx import Document as PyHwpxDocument
from pywpdoc.docx import Document as PyDocxDocument
from pywpdoc._engine.common import Document as BaselineCommonDocument
from pywpdoc._engine import Document as BaselineNativeHwpxDocument


def _part_hashes(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as zf:
        return {
            name: hashlib.sha256(zf.read(name)).hexdigest()
            for name in sorted(zf.namelist())
        }


def _selected_docx_hashes(path: Path) -> dict[str, str]:
    names = {
        "word/document.xml",
        "word/styles.xml",
        "word/settings.xml",
        "word/fontTable.xml",
        "word/_rels/document.xml.rels",
    }
    with zipfile.ZipFile(path) as zf:
        available = set(zf.namelist())
        return {
            name: hashlib.sha256(zf.read(name)).hexdigest()
            for name in sorted(names & available)
        }


def test_pywpdoc_root_is_high_level_common_facade() -> None:
    hwpx = PyDocument.new("hwpx")
    docx = PyDocument.new("docx")
    assert hwpx.format == "hwpx"
    assert docx.format == "docx"
    assert isinstance(hwpx.backend, PyHwpxDocument)
    assert isinstance(docx.backend, PyDocxDocument)


def test_backend_specific_entry_points_remain_first_class() -> None:
    assert PyHwpxDocument.new().format == "hwpx"
    assert PyDocxDocument.new().format == "docx"


def test_legacy_root_document_semantics_are_preserved() -> None:
    # The migration does not silently change old user code.  The old package
    # root still exposes the native HWPX engine until the compatibility window
    # is explicitly retired.
    legacy = BaselineNativeHwpxDocument.new()
    legacy.add_paragraph("legacy")
    assert legacy.paragraphs[-1].text == "legacy"


def test_unwrap_is_explicit_backend_escape_hatch() -> None:
    for kind in ("hwpx", "docx"):
        doc = PyDocument.new(kind)
        assert doc.unwrap() is doc.native


def test_pywpdoc_hwpx_rebuild_matches_v0215_baseline_and_source(tmp_path: Path) -> None:
    source = Path(__file__).parent / "fixtures" / "original_notice.hwpx"
    baseline = BaselineCommonDocument.rebuild(source, format="hwpx", preserve_layout=True)
    migrated = PyDocument.rebuild(source, format="hwpx", preserve_layout=True)
    a = tmp_path / "baseline.hwpx"
    b = tmp_path / "pywpdoc.hwpx"
    baseline.save(a)
    migrated.save(b)
    assert _part_hashes(a) == _part_hashes(b)
    assert _part_hashes(b) == _part_hashes(source)


def test_pywpdoc_docx_rebuild_matches_v0215_conversion_output(tmp_path: Path) -> None:
    source = Path(__file__).parent / "fixtures" / "original_notice.hwpx"
    baseline = BaselineCommonDocument.rebuild(source, format="docx", preserve_layout=True)
    migrated = PyDocument.rebuild(source, format="docx", preserve_layout=True)
    a = tmp_path / "baseline.docx"
    b = tmp_path / "pywpdoc.docx"
    baseline.save(a)
    migrated.save(b)
    assert _selected_docx_hashes(a) == _selected_docx_hashes(b)


def test_feature_namespace_import_has_no_document_side_effect(tmp_path: Path) -> None:
    # Use a preserved-layout rebuild rather than two newly-authored documents:
    # the legacy native engine allocates some object ids process-globally, so
    # independently authored files are not a valid byte-for-byte isolation oracle.
    source = Path(__file__).parent / "fixtures" / "original_notice.hwpx"
    before = PyDocument.rebuild(source, format="hwpx", preserve_layout=True)
    a = tmp_path / "before.hwpx"
    before.save(a)

    importlib.import_module("pywpdoc.features")

    after = PyDocument.rebuild(source, format="hwpx", preserve_layout=True)
    b = tmp_path / "after.hwpx"
    after.save(b)
    assert _part_hashes(a) == _part_hashes(b) == _part_hashes(source)
