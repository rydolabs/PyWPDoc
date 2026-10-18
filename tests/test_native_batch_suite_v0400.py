"""Native-editor master-probe batch: case-level failure isolation and fail-closed checks."""
from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from lxml import etree
import pytest

from pywpdoc import Document
from tests.quality.native_batch_suite import (
    CASES, create_suite, evaluate_case, inspect_batch, run_suite,
)


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "native_batch"
    create_suite(root)
    return root, root / "01_BATCH_BASE.hwpx"


def test_batch_generator_emits_one_valid_document_for_ten_distinct_cases(tmp_path: Path):
    root, baseline = _setup(tmp_path)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    baseline_info = inspect_batch(baseline)
    assert len(CASES) == len(manifest["cases"]) == 10
    assert set(baseline_info["tables"]) == {x["id"] for x in CASES}
    assert baseline_info["track_changes"] == []
    assert (root / "INSTRUCTIONS_KO.md").exists()


def test_no_observation_generates_all_skip_not_false_failures(tmp_path: Path):
    root, _ = _setup(tmp_path)
    result = run_suite(root, None, tmp_path / "report")
    assert result["counts"] == {"SKIP": 10}
    assert len((tmp_path / "report" / "issues.log").read_text(encoding="utf-8").splitlines()) == 10
    assert all(not r["review_semantics_verified"] for r in result["cases"])


def test_batch_plain_edits_log_fails_and_untracked_and_continue(tmp_path: Path):
    root, baseline = _setup(tmp_path)
    doc = Document.open(baseline)
    doc.tables[0].cell(1, 1).text = "ABCD"  # plain text edit; no revision
    doc.tables[1].cell(1, 1).text = "ABC"  # plain deletion; no revision
    row = doc.tables[5]
    row.insert_row(2, row.clone_row(1))
    row.cell(2, 0).text = "X"
    row.cell(2, 1).text = "9"
    doc.tables[6].remove_row(2)
    modified = tmp_path / "plain.hwpx"
    doc.save(modified)
    result = run_suite(root, modified, tmp_path / "report")
    statuses = {r["id"]: r["status"] for r in result["cases"]}
    assert statuses["T01_INSERT"] == statuses["T02_DELETE"] == "FAIL"
    assert statuses["S06_ROW_INSERT"] == statuses["S07_ROW_DELETE"] == "UNTRACKED"
    assert statuses["T03_REPLACE"] == statuses["S10_CELL_MERGE"] == "SKIP"
    assert sum(result["counts"].values()) == 10
    assert (tmp_path / "report" / "results.csv").exists()
    assert (tmp_path / "report" / "results.md").exists()
    assert "S07_ROW_DELETE" in (tmp_path / "report" / "issues.log").read_text(encoding="utf-8")


def test_case_error_does_not_stop_independent_case(tmp_path: Path):
    root, baseline = _setup(tmp_path)
    old = inspect_batch(baseline)
    modified = inspect_batch(baseline)
    del modified["tables"]["T01_INSERT"]
    first = next(c for c in CASES if c["id"] == "T01_INSERT")
    with pytest.raises(ValueError, match="header ID missing"):
        evaluate_case(first, old, modified, [])
    other = next(c for c in CASES if c["id"] == "T02_DELETE")
    assert evaluate_case(other, old, modified, [])["status"] == "SKIP"


def test_single_corrupted_input_creates_all_error_logs_without_crashing(tmp_path: Path):
    root, _ = _setup(tmp_path)
    corrupted = tmp_path / "bad.hwpx"
    corrupted.write_bytes(b"broken zip")
    report = run_suite(root, corrupted, tmp_path / "reports")
    assert report["counts"] == {"ERROR": 10}
    assert len((tmp_path / "reports" / "issues.log").read_text(encoding="utf-8").splitlines()) == 10


def test_detects_locally_anchored_text_revision_not_global_only(tmp_path: Path):
    root, baseline = _setup(tmp_path)
    base = inspect_batch(baseline)
    synthetic = inspect_batch(baseline)
    item = synthetic["tables"]["T01_INSERT"]
    item["markers"] = [{"kind":"insertBegin", "attrs":{"Id":"9", "TcId":"1"}}, {"kind":"insertEnd", "attrs":{"Id":"9", "TcId":"1"}}]
    item["target_markers"] = list(item["markers"])
    item["rows"][1][1] = "ABCD"
    case = CASES[0]
    assert evaluate_case(case, base, synthetic, [{"type":"Insert", "id":"1"}])["status"] == "PASS"
    assert evaluate_case(case, base, synthetic, [{"type":"Insert", "id":"2"}])["status"] == "FAIL"
    # A change elsewhere in the document must not make T01 pass.
    item["markers"] = []
    item["target_markers"] = []
    assert evaluate_case(case, base, synthetic, [{"type":"Insert"}])["status"] == "FAIL"


def test_row_revision_candidate_is_review_not_auto_pass(tmp_path: Path):
    root, baseline = _setup(tmp_path)
    base = inspect_batch(baseline)
    synthetic = inspect_batch(baseline)
    row = synthetic["tables"]["S06_ROW_INSERT"]
    row["rows"].append(["X", "9"])
    row["row_count"] += 1
    row["row_revision_candidates"] = [{"element":"tr", "attrs":{"rowRevisionId":"123"}}]
    case = next(c for c in CASES if c["id"] == "S06_ROW_INSERT")
    result = evaluate_case(case, base, synthetic, [])
    assert result["status"] == "REVIEW"
    assert result["review_semantics_verified"] is False


def test_baseline_checksum_guard(tmp_path: Path):
    root, baseline = _setup(tmp_path)
    baseline.write_bytes(baseline.read_bytes() + b"mutation")
    with pytest.raises(ValueError, match="sha256"):
        run_suite(root, None, tmp_path / "reports")


def test_structural_case_not_falsely_certified_by_inserted_cell_text(tmp_path: Path):
    root, baseline = _setup(tmp_path)
    before = inspect_batch(baseline)
    edited = inspect_batch(baseline)
    item = edited["tables"]["S06_ROW_INSERT"]
    item["row_count"] += 1
    item["rows"].append(["X", "9"])
    item["markers"] = [{"kind":"insertBegin", "attrs":{"Id":"3", "TcId":"1"}},
                       {"kind":"insertEnd", "attrs":{"Id":"3", "TcId":"1"}}]
    case = next(c for c in CASES if c["id"] == "S06_ROW_INSERT")
    result = evaluate_case(case, before, edited, [{"type":"Insert", "id":"1"}])
    assert result["status"] == "UNTRACKED"
    assert "only text/format" in result["reason"]


def test_format_changed_without_revision_reports_fail(tmp_path: Path):
    root, baseline = _setup(tmp_path)
    before = inspect_batch(baseline)
    edited = inspect_batch(baseline)
    edited["tables"]["T04_CHAR"]["formats"][1][1]["char_refs"] = ["12345"]
    case = next(c for c in CASES if c["id"] == "T04_CHAR")
    result = evaluate_case(case, before, edited, [])
    assert result["status"] == "FAIL"


def test_revision_in_wrong_cell_does_not_pass_target_case(tmp_path: Path):
    root, baseline = _setup(tmp_path)
    base = inspect_batch(baseline)
    synthetic = inspect_batch(baseline)
    item = synthetic["tables"]["T01_INSERT"]
    item["markers"] = [{"kind":"insertBegin", "attrs":{"Id":"9", "TcId":"1"}},
                       {"kind":"insertEnd", "attrs":{"Id":"9", "TcId":"1"}}]
    item["target_markers"] = []
    item["rows"][1][1] = "ABCD"
    assert evaluate_case(CASES[0], base, synthetic, [{"type":"Insert", "id":"1"}])["status"] == "FAIL"
