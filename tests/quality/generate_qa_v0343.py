"""Generate v0.34.3 HWPX release-QA scenarios with machine-checkable manifests.

The purpose of this generator is to prevent unrelated OLD/NEW/TRACKED files
from being presented as one scenario.  Formatting tracking is intentionally
unsupported for HWPX until a native Hancom-authored formatting-revision sample
is available; text tracking remains a positive control.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pywpdoc import Document, DocumentUnsupportedError
from pywpdoc._engine import validate_hwpx_file

DATE = "2026-10-10T00:00:00Z"
AUTHOR = "PyWPDoc QA"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _validate(path: Path) -> None:
    result = validate_hwpx_file(path)
    if not result.ok:
        raise RuntimeError(f"validator rejected {path}: {result.issues}")
    Document.open(path)


def generate_format_unsupported(root: Path) -> dict[str, Any]:
    out = root / "qa_hwpx_format_unsupported_v0343"
    out.mkdir(parents=True, exist_ok=True)

    old = Document.new("hwpx")
    p_old = old.add_paragraph()
    p_old.add_run("Character formatting: ")
    old_changed = p_old.add_run("Alpha Beta")
    old_changed.font.size = 10

    new = Document.new("hwpx")
    p_new = new.add_paragraph()
    p_new.add_run("Character formatting: ")
    new_changed = p_new.add_run("Alpha Beta")
    new_changed.font.size = 14
    new_changed.bold = True

    old_path = out / "format_old_v0343.hwpx"
    new_path = out / "format_new_v0343.hwpx"
    old.save(old_path)
    new.save(new_path)
    _validate(old_path)
    _validate(new_path)

    try:
        old.compare(new, author=AUTHOR, date=DATE, everywhere=False)
    except DocumentUnsupportedError as exc:
        code = exc.code
    else:
        raise RuntimeError("HWPX formatting compare unexpectedly emitted a review document")
    if code != "compare-hwpx-format-track-unsupported":
        raise RuntimeError(f"unexpected HWPX formatting error code: {code}")

    manifest = {
        "schema": "pywpdoc-release-qa/v1",
        "release": "0.34.3",
        "scenario_id": "hwpx-formatting-unsupported",
        "status": "expected-fail-closed",
        "format": "hwpx",
        "purpose": "HWPX character-format difference must not emit a misleading Track Changes document.",
        "old": {
            "file": old_path.name,
            "sha256": _sha256(old_path),
            "plain_text": "Character formatting: Alpha Beta",
            "changed_span": "Alpha Beta",
            "font_size_pt": 10,
            "bold": False,
        },
        "new": {
            "file": new_path.name,
            "sha256": _sha256(new_path),
            "plain_text": "Character formatting: Alpha Beta",
            "changed_span": "Alpha Beta",
            "font_size_pt": 14,
            "bold": True,
        },
        "tracked": None,
        "expected_error_code": "compare-hwpx-format-track-unsupported",
        "native_hancom_fixture_required_before_support": True,
    }
    _write_json(out / "manifest.json", manifest)
    (out / "NO_TRACKED_FILE_EXPECTED.txt").write_text(
        "This scenario intentionally has no TRACKED HWPX.\n"
        "Expected error: compare-hwpx-format-track-unsupported\n"
        "A native Hancom-authored formatting-revision HWPX is required before this feature can be enabled.\n",
        encoding="utf-8",
    )
    return manifest


def generate_text_tracking(root: Path) -> dict[str, Any]:
    out = root / "qa_hwpx_text_tracking_v0343"
    out.mkdir(parents=True, exist_ok=True)

    old = Document.new("hwpx")
    new = Document.new("hwpx")
    old.add_paragraph("Text tracking: old value")
    new.add_paragraph("Text tracking: new value")

    old_path = out / "text_old_v0343.hwpx"
    new_path = out / "text_new_v0343.hwpx"
    tracked_path = out / "text_tracked_review_v0343.hwpx"
    old.save(old_path)
    new.save(new_path)
    old.compare(new, author=AUTHOR, date=DATE, everywhere=False).save(tracked_path)
    for path in (old_path, new_path, tracked_path):
        _validate(path)

    reopened_old = Document.open(old_path)
    reopened_new = Document.open(new_path)
    reopened_tracked = Document.open(tracked_path)
    manifest = {
        "schema": "pywpdoc-release-qa/v1",
        "release": "0.34.3",
        "scenario_id": "hwpx-text-tracking-control",
        "status": "supported-positive-control",
        "format": "hwpx",
        "purpose": "OLD/NEW/TRACKED are the same text-change scenario and prove HWPX text Track Changes remains enabled.",
        "old": {
            "file": old_path.name,
            "sha256": _sha256(old_path),
            "plain_text": reopened_old.paragraphs[-1].text,
        },
        "new": {
            "file": new_path.name,
            "sha256": _sha256(new_path),
            "plain_text": reopened_new.paragraphs[-1].text,
        },
        "tracked": {
            "file": tracked_path.name,
            "sha256": _sha256(tracked_path),
            "logical_text_projection": reopened_tracked.paragraphs[-1].text,
            "author": AUTHOR,
            "date": DATE,
        },
        "expected_accept_all_plain_text": "Text tracking: new value",
        "expected_reject_all_plain_text": "Text tracking: old value",
    }
    _write_json(out / "manifest.json", manifest)
    return manifest


def generate_all(root: Path) -> None:
    root = root.resolve()
    format_manifest = generate_format_unsupported(root)
    text_manifest = generate_text_tracking(root)
    index = {
        "schema": "pywpdoc-release-qa-index/v1",
        "release": "0.34.3",
        "scenarios": [
            {
                "scenario_id": format_manifest["scenario_id"],
                "directory": "qa_hwpx_format_unsupported_v0343",
                "status": format_manifest["status"],
                "tracked_file_expected": False,
            },
            {
                "scenario_id": text_manifest["scenario_id"],
                "directory": "qa_hwpx_text_tracking_v0343",
                "status": text_manifest["status"],
                "tracked_file_expected": True,
            },
        ],
        "rule": "Never present artifacts from different scenario_id values as one OLD/NEW/TRACKED set.",
    }
    _write_json(root / "QA_INDEX_V0343.json", index)


if __name__ == "__main__":
    generate_all(Path.cwd())
