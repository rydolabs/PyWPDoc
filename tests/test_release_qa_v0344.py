"""Release-QA integrity checks for v0.34.4 native-backed CharShape tracking."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from pywpdoc import Document
from pywpdoc._engine import validate_hwpx_file

ROOT = Path(__file__).resolve().parents[1]
HH = "http://www.hancom.co.kr/hwpml/2011/head"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS = {"hh": HH, "hp": HP}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(directory: str):
    return json.loads((ROOT / "tests/fixtures/historical" / directory / "manifest.json").read_text(encoding="utf-8"))


def test_v0344_index_has_matching_tracked_files_for_both_positive_controls():
    index = json.loads((ROOT / "docs/maintainers/QA_INDEX_V0344.json").read_text(encoding="utf-8"))
    assert index["release"] == "0.34.4"
    assert {s["scenario_id"] for s in index["scenarios"]} == {
        "hwpx-char-format-tracking-hancom2020", "hwpx-text-tracking-control"
    }
    assert all(s["tracked_file_expected"] for s in index["scenarios"])


def test_char_format_qa_matches_native_hancom2020_contract():
    directory = ROOT / "tests/fixtures/historical/qa_hwpx_char_format_v0344"
    manifest = _manifest(directory.name)
    for role in ("old", "new", "tracked"):
        path = directory / manifest[role]["file"]
        assert path.exists()
        assert _sha256(path) == manifest[role]["sha256"]
        assert validate_hwpx_file(path).ok

    tracked = directory / manifest["tracked"]["file"]
    with ZipFile(tracked) as zf:
        header = etree.fromstring(zf.read("Contents/header.xml"))
        section = etree.fromstring(zf.read("Contents/section0.xml"))
    changes = header.xpath('.//hh:trackChange[@type="CharShape"]', namespaces=NS)
    anchors = section.xpath('.//hp:run[@paraTcId]', namespaces=NS)
    assert len(changes) == manifest["tracked"]["charshape_change_count"] == 3
    assert len(anchors) == manifest["tracked"]["run_paraTcId_count"] == 3
    assert all(c.get("charshapeID") is not None and c.get("charShapeID") is None for c in changes)
    assert not section.xpath('.//hp:run[@charTcId]', namespaces=NS)
    assert not section.xpath('.//hp:insertBegin | .//hp:deleteBegin', namespaces=NS)


def test_char_format_qa_text_is_identical_old_new_tracked():
    directory = ROOT / "tests/fixtures/historical/qa_hwpx_char_format_v0344"
    manifest = _manifest(directory.name)
    docs = [Document.open(directory / manifest[role]["file"]) for role in ("old", "new", "tracked")]
    texts = [[p.text for p in doc.paragraphs] for doc in docs]
    assert texts[0] == texts[1] == texts[2]
    assert any("Alpha Beta" in text for text in texts[0])


def test_native_contract_receipt_records_supplied_hancom2020_oracle():
    contract = json.loads((ROOT / "tests/fixtures/hancom2020_charshape_track_contract.json").read_text())
    assert contract["source_sha256"] == "3977565ba3377155c82170e2524ed06d6d0dc4e3b7cd0430d499ffa4d5477e5b"
    assert contract["track_change"]["type"] == "CharShape"
    assert contract["track_change"]["charshapeID"] == "0"
    assert contract["native_anchor_attribute"] == "paraTcId"
    assert contract["new_charpr"] == {"height": "1600", "bold": True}
