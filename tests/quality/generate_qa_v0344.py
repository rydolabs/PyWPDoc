"""Generate v0.34.4 HWPX release-QA scenarios.

The character-format scenario is backed by a real Hancom 2020 authored
CharShape revision supplied during GUI QA.  The native contract is recorded in
``tests/fixtures/hancom2020_charshape_track_contract.json``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any
from zipfile import ZipFile

from lxml import etree

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pywpdoc import Document
from pywpdoc._engine import validate_hwpx_file

DATE = "2026-10-12T11:26:00Z"
AUTHOR = "user"
HH = "http://www.hancom.co.kr/hwpml/2011/head"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS = {"hh": HH, "hp": HP}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _validate(path: Path) -> None:
    result = validate_hwpx_file(path)
    if not result.ok:
        raise RuntimeError(f"validator rejected {path}: {result.issues}")
    Document.open(path)


def _char_format_documents() -> tuple[Document, Document]:
    old = Document.new("hwpx")
    new = Document.new("hwpx")

    rows = [
        ("Font + bold + size: ", "Alpha Beta"),
        ("Bold only: ", "Gamma Delta"),
        ("Font only: ", "Sample Text"),
    ]
    for prefix, target in rows:
        op = old.add_paragraph()
        op.add_run(prefix)
        op.add_run(target)
        np = new.add_paragraph()
        np.add_run(prefix)
        nr = np.add_run(target)
        if target == "Alpha Beta":
            nr.font.name = "Arial"
            nr.bold = True
            nr.font.size = 16
        elif target == "Gamma Delta":
            nr.bold = True
        else:
            nr.font.name = "Arial"
    return old, new


def generate_char_format_tracking(root: Path) -> dict[str, Any]:
    out = root / "qa_hwpx_char_format_v0344"
    out.mkdir(parents=True, exist_ok=True)
    old, new = _char_format_documents()

    old_path = out / "char_format_old_v0344.hwpx"
    new_path = out / "char_format_new_v0344.hwpx"
    tracked_path = out / "char_format_tracked_review_v0344.hwpx"
    old.save(old_path)
    new.save(new_path)
    old.compare(new, author=AUTHOR, date=DATE, everywhere=False).save(tracked_path)
    for path in (old_path, new_path, tracked_path):
        _validate(path)

    with ZipFile(tracked_path) as zf:
        header = etree.fromstring(zf.read("Contents/header.xml"))
        section = etree.fromstring(zf.read("Contents/section0.xml"))
    changes = header.xpath('.//hh:trackChange[@type="CharShape"]', namespaces=NS)
    anchors = section.xpath('.//hp:run[@paraTcId]', namespaces=NS)
    legacy_anchors = section.xpath('.//hp:run[@charTcId]', namespaces=NS)
    text_marks = section.xpath('.//hp:insertBegin | .//hp:insertEnd | .//hp:deleteBegin | .//hp:deleteEnd', namespaces=NS)
    if len(changes) != 3 or len(anchors) != 3 or legacy_anchors or text_marks:
        raise RuntimeError(
            f"unexpected CharShape QA structure: changes={len(changes)} anchors={len(anchors)} "
            f"charTcId={len(legacy_anchors)} text_marks={len(text_marks)}"
        )
    if any(c.get("charshapeID") is None or c.get("charShapeID") is not None for c in changes):
        raise RuntimeError("CharShape QA did not use Hancom 2020 native charshapeID spelling")

    manifest = {
        "schema": "pywpdoc-release-qa/v1",
        "release": "0.34.4",
        "scenario_id": "hwpx-char-format-tracking-hancom2020",
        "status": "native-oracle-backed-candidate",
        "format": "hwpx",
        "purpose": "Formatting-only Track Changes: font, bold, and size changes with identical text.",
        "native_oracle_contract": "tests/fixtures/hancom2020_charshape_track_contract.json",
        "old": {"file": old_path.name, "sha256": _sha256(old_path)},
        "new": {"file": new_path.name, "sha256": _sha256(new_path)},
        "tracked": {
            "file": tracked_path.name,
            "sha256": _sha256(tracked_path),
            "charshape_change_count": len(changes),
            "run_paraTcId_count": len(anchors),
            "run_charTcId_count": len(legacy_anchors),
            "text_revision_marker_count": len(text_marks),
            "author": AUTHOR,
            "date": DATE,
        },
        "expected_accept_all": "NEW formatting",
        "expected_reject_all": "OLD formatting",
        "gui_verification_required": True,
        "paragraph_format_tracking": "unsupported-until-native-ParaShape-oracle",
    }
    _write_json(out / "manifest.json", manifest)
    return manifest


def generate_text_tracking(root: Path) -> dict[str, Any]:
    out = root / "qa_hwpx_text_tracking_v0344"
    out.mkdir(parents=True, exist_ok=True)
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    old.add_paragraph("Text tracking: old value")
    new.add_paragraph("Text tracking: new value")
    old_path = out / "text_old_v0344.hwpx"
    new_path = out / "text_new_v0344.hwpx"
    tracked_path = out / "text_tracked_review_v0344.hwpx"
    old.save(old_path)
    new.save(new_path)
    old.compare(new, author=AUTHOR, date=DATE, everywhere=False).save(tracked_path)
    for path in (old_path, new_path, tracked_path):
        _validate(path)
    manifest = {
        "schema": "pywpdoc-release-qa/v1",
        "release": "0.34.4",
        "scenario_id": "hwpx-text-tracking-control",
        "status": "supported-positive-control",
        "format": "hwpx",
        "old": {"file": old_path.name, "sha256": _sha256(old_path)},
        "new": {"file": new_path.name, "sha256": _sha256(new_path)},
        "tracked": {"file": tracked_path.name, "sha256": _sha256(tracked_path)},
    }
    _write_json(out / "manifest.json", manifest)
    return manifest


def generate_all(root: Path) -> None:
    root = root.resolve()
    char_format = generate_char_format_tracking(root)
    text = generate_text_tracking(root)
    index = {
        "schema": "pywpdoc-release-qa-index/v1",
        "release": "0.34.4",
        "scenarios": [
            {"scenario_id": char_format["scenario_id"], "directory": "qa_hwpx_char_format_v0344", "tracked_file_expected": True},
            {"scenario_id": text["scenario_id"], "directory": "qa_hwpx_text_tracking_v0344", "tracked_file_expected": True},
        ],
    }
    _write_json(root / "QA_INDEX_V0344.json", index)


if __name__ == "__main__":
    generate_all(Path(__file__).resolve().parents[1])
