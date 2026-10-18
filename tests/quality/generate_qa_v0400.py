"""Generate v0.40.0 HWPX native table-row Track Changes probe artifacts."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pywpdoc import Document, DocumentUnsupportedError
from pywpdoc._engine import validate_hwpx_file
from tests.quality.analyze_hwpx_row_tracking import compare_hwpx


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _table_doc(rows: list[tuple[str, str]]) -> Document:
    doc = Document.new("hwpx")
    doc.add_paragraph("HWPX native row Track Changes probe")
    table = doc.add_table(len(rows), 2, style="Table Grid")
    for i, (left, right) in enumerate(rows):
        table.cell(i, 0).text = left
        table.cell(i, 1).text = right
    return doc


def _save_valid(doc: Document, path: Path) -> None:
    doc.save(path)
    result = validate_hwpx_file(path)
    if not result.ok:
        raise RuntimeError(f"validation failed for {path}: {result.issues}")


def _assert_fail_closed(old: Document, new: Document) -> str:
    try:
        old.compare(new, author="PyWPDoc QA", date="2026-10-13T00:00:00Z")
    except DocumentUnsupportedError as exc:
        if exc.code != "compare-hwpx-table-row-track-unsupported":
            raise
        return exc.code
    raise RuntimeError("HWPX row structural comparison unexpectedly succeeded")


def generate(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)

    insert_base = _table_doc([("A", "1"), ("B", "2"), ("C", "3")])
    insert_expected = _table_doc([("A", "1"), ("X", "9"), ("B", "2"), ("C", "3")])
    delete_base = _table_doc([("A", "1"), ("B", "2"), ("C", "3")])
    delete_expected = _table_doc([("A", "1"), ("C", "3")])

    files = {
        "insert_base": root / "row_insert_probe_base_v0400.hwpx",
        "insert_expected": root / "row_insert_expected_final_v0400.hwpx",
        "delete_base": root / "row_delete_probe_base_v0400.hwpx",
        "delete_expected": root / "row_delete_expected_final_v0400.hwpx",
    }
    _save_valid(insert_base, files["insert_base"])
    _save_valid(insert_expected, files["insert_expected"])
    _save_valid(delete_base, files["delete_base"])
    _save_valid(delete_expected, files["delete_expected"])

    insert_code = _assert_fail_closed(insert_base, insert_expected)
    delete_code = _assert_fail_closed(delete_base, delete_expected)

    plain_insert_report = compare_hwpx(files["insert_base"], files["insert_expected"], files["insert_expected"])
    plain_delete_report = compare_hwpx(files["delete_base"], files["delete_expected"], files["delete_expected"])
    (root / "plain_insert_structure_delta_analysis.json").write_text(json.dumps(plain_insert_report, ensure_ascii=False, indent=2) + "\n")
    (root / "plain_delete_structure_delta_analysis.json").write_text(json.dumps(plain_delete_report, ensure_ascii=False, indent=2) + "\n")

    instructions = """HWPX table-row Track Changes native probe (Hancom 2020)\n\nINSERT probe\n1. Open row_insert_probe_base_v0400.hwpx in Hancom 2020.\n2. Turn Review > Track Changes ON.\n3. Insert one row between A/1 and B/2.\n4. Enter X in the left cell and 9 in the right cell.\n5. Do NOT accept/reject changes. Save as HWPX.\n\nDELETE probe\n1. Open row_delete_probe_base_v0400.hwpx in Hancom 2020.\n2. Turn Review > Track Changes ON.\n3. Delete the entire B/2 row.\n4. Do NOT accept/reject changes. Save as HWPX.\n\nUpload the saved HWPX file(s), not PDF. The analyzer will compare package entries, header trackChanges, inline markers, paragraph/run anchors, table row XML, and any history/version-log parts.\n"""
    (root / "NATIVE_ROW_TRACKING_PROBE_INSTRUCTIONS.txt").write_text(instructions, encoding="utf-8")

    manifest = {
        "schema": "pywpdoc-release-qa/v1",
        "release": "0.40.0-candidate",
        "scenario_id": "hwpx-native-table-row-tracking-probe",
        "status": "native-oracle-required-fail-closed",
        "public_model_evidence": {
            "track_change_types": ["Insert", "Delete", "CharShape", "ParaShape"],
            "insert_delete_marker_scope": "hp:t mixed content in Hancom public OWPML model",
            "verified_hp_tr_revision_anchor": False,
        },
        "compare_error_code": insert_code,
        "insert": {
            "baseline": {"file": files["insert_base"].name, "sha256": _sha(files["insert_base"])},
            "expected_final": {"file": files["insert_expected"].name, "sha256": _sha(files["insert_expected"])},
            "native_tracked": None,
            "operation": "insert row X/9 between A/1 and B/2 while Track Changes is ON",
        },
        "delete": {
            "baseline": {"file": files["delete_base"].name, "sha256": _sha(files["delete_base"])},
            "expected_final": {"file": files["delete_expected"].name, "sha256": _sha(files["delete_expected"])},
            "native_tracked": None,
            "operation": "delete entire B/2 row while Track Changes is ON",
            "compare_error_code": delete_code,
        },
        "analyzer": "quality/analyze_hwpx_row_tracking.py",
        "rule": "Do not enable HWPX row-level Track Changes until a Hancom-authored unaccepted row-change HWPX establishes an Accept/Reject representation.",
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    index = {"release": "0.40.0-candidate", "scenarios": [{
        "scenario_id": manifest["scenario_id"], "directory": root.name, "status": manifest["status"],
    }]}
    (root.parent / "QA_INDEX_V0400.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    generate(ROOT / "tests/fixtures/historical/qa_hwpx_row_tracking_probe_v0400")
