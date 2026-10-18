"""Release-QA integrity checks for v0.34.3.

These tests make it impossible to accidentally package an unrelated TRACKED
file beside formatting OLD/NEW files and call the three a comparison set.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from pywpdoc import Document, DocumentUnsupportedError
from pywpdoc.features.compare import build_revision_plan
from pywpdoc._engine import validate_hwpx_file

ROOT = Path(__file__).resolve().parents[1]
HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
HH = "{http://www.hancom.co.kr/hwpml/2011/head}"


def _manifest(directory: str):
    return json.loads((ROOT / "tests/fixtures/historical" / directory / "manifest.json").read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_qa_index_separates_unsupported_formatting_from_text_tracking():
    index = json.loads((ROOT / "docs/maintainers/QA_INDEX_V0343.json").read_text(encoding="utf-8"))
    scenarios = {item["scenario_id"]: item for item in index["scenarios"]}
    assert scenarios["hwpx-formatting-unsupported"]["tracked_file_expected"] is False
    assert scenarios["hwpx-text-tracking-control"]["tracked_file_expected"] is True
    assert scenarios["hwpx-formatting-unsupported"]["directory"] != scenarios["hwpx-text-tracking-control"]["directory"]


def test_v0343_formatting_qa_remains_a_historical_fail_closed_receipt():
    directory = ROOT / "tests/fixtures/historical/qa_hwpx_format_unsupported_v0343"
    manifest = _manifest(directory.name)
    assert manifest["scenario_id"] == "hwpx-formatting-unsupported"
    assert manifest["tracked"] is None
    assert not list(directory.glob("*tracked*.hwpx"))

    old_path = directory / manifest["old"]["file"]
    new_path = directory / manifest["new"]["file"]
    assert _sha256(old_path) == manifest["old"]["sha256"]
    assert _sha256(new_path) == manifest["new"]["sha256"]
    assert validate_hwpx_file(old_path).ok and validate_hwpx_file(new_path).ok

    old = Document.open(old_path)
    new = Document.open(new_path)
    assert old.paragraphs[-1].text == new.paragraphs[-1].text == "Character formatting: Alpha Beta"
    plan = build_revision_plan(old, new, everywhere=False)
    assert plan.run_formats
    # v0.34.3 recorded the then-correct fail-closed policy. v0.34.4 supersedes
    # that policy after a native Hancom 2020 CharShape oracle was supplied.
    assert manifest["expected_error_code"] == "compare-hwpx-format-track-unsupported"
    current = json.loads((ROOT / "docs/maintainers/QA_INDEX_V0344.json").read_text(encoding="utf-8"))
    assert any(s["scenario_id"] == "hwpx-char-format-tracking-hancom2020" for s in current["scenarios"])


def test_text_tracking_qa_is_one_matching_old_new_tracked_scenario():
    directory = ROOT / "tests/fixtures/historical/qa_hwpx_text_tracking_v0343"
    manifest = _manifest(directory.name)
    assert manifest["scenario_id"] == "hwpx-text-tracking-control"

    old_path = directory / manifest["old"]["file"]
    new_path = directory / manifest["new"]["file"]
    tracked_path = directory / manifest["tracked"]["file"]
    for role, path in (("old", old_path), ("new", new_path), ("tracked", tracked_path)):
        assert _sha256(path) == manifest[role]["sha256"]
        assert validate_hwpx_file(path).ok

    assert Document.open(old_path).paragraphs[-1].text == "Text tracking: old value"
    assert Document.open(new_path).paragraphs[-1].text == "Text tracking: new value"

    with ZipFile(tracked_path) as zf:
        section = etree.fromstring(zf.read("Contents/section0.xml"))
        header = etree.fromstring(zf.read("Contents/header.xml"))
    marks = [etree.QName(e).localname for e in section.iter() if etree.QName(e).localname in {"insertBegin", "insertEnd", "deleteBegin", "deleteEnd"}]
    assert {"insertBegin", "insertEnd", "deleteBegin", "deleteEnd"}.issubset(set(marks))
    change_types = {e.get("type") for e in header.iter(f"{HH}trackChange")}
    assert {"Insert", "Delete"}.issubset(change_types)


def test_v0343_current_qa_does_not_reuse_v0342_confusing_filename_set():
    current_dirs = [ROOT / "tests/fixtures/historical/qa_hwpx_format_unsupported_v0343", ROOT / "tests/fixtures/historical/qa_hwpx_text_tracking_v0343"]
    current_files = {p.name for d in current_dirs for p in d.iterdir() if p.is_file()}
    assert "text_tracked_review_v0342.hwpx" not in current_files
    assert "format_old_v0342.hwpx" not in current_files
    assert "format_new_v0342.hwpx" not in current_files
