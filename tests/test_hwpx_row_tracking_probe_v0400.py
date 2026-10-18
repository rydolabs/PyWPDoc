"""v0.40.0 HWPX row Track Changes native-oracle probe and analyzer tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pywpdoc import Document, DocumentUnsupportedError
from tests.quality.analyze_hwpx_row_tracking import compare_hwpx, inspect_hwpx
from tests.quality.generate_qa_v0400 import generate

ROOT = Path(__file__).resolve().parents[1]


def _table_doc(rows: list[tuple[str, str]]) -> Document:
    doc = Document.new("hwpx")
    table = doc.add_table(len(rows), 2, style="Table Grid")
    for i, (a, b) in enumerate(rows):
        table.cell(i, 0).text = a
        table.cell(i, 1).text = b
    return doc


def test_hwpx_row_compare_remains_fail_closed_with_specific_code():
    old = _table_doc([("A", "1"), ("B", "2")])
    new = _table_doc([("A", "1"), ("X", "9"), ("B", "2")])
    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new, author="QA")
    assert excinfo.value.code == "compare-hwpx-table-row-track-unsupported"
    assert "native" in (excinfo.value.suggestion or "").lower() or "hancom" in (excinfo.value.suggestion or "").lower()


def test_analyzer_classifies_plain_row_delta_as_structure_without_revision(tmp_path: Path):
    old = _table_doc([("A", "1"), ("B", "2")])
    new = _table_doc([("A", "1"), ("X", "9"), ("B", "2")])
    old_path = tmp_path / "old.hwpx"
    new_path = tmp_path / "new.hwpx"
    old.save(old_path)
    new.save(new_path)
    report = compare_hwpx(old_path, new_path, new_path)
    assert report["delta"]["structure_changed"] is True
    assert report["classification"]["track_change_types"] == []
    assert report["classification"]["row_specific_revision_anchor_detected"] is False
    assert report["classification"]["safe_to_synthesize_row_tracking_from_public_model"] is False


def test_analyzer_sees_existing_text_tracking_markers_as_t_scoped():
    tracked = ROOT / "tests/fixtures/historical/qa_hwpx_text_tracking_v0344" / "text_tracked_review_v0344.hwpx"
    info = inspect_hwpx(tracked)
    assert info["track_changes"]
    assert {c.get("type") for c in info["track_changes"]} >= {"Insert", "Delete"}
    assert info["inline_markers"]
    assert {m["parent"] for m in info["inline_markers"]} == {"t"}
    assert info["row_revision_anchor_candidates"] == []


def test_v0400_generator_emits_separate_native_probe_scenarios(tmp_path: Path):
    root = tmp_path / "qa_hwpx_row_tracking_probe_v0400"
    generate(root)
    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["status"] == "native-oracle-required-fail-closed"
    assert manifest["insert"]["native_tracked"] is None
    assert manifest["delete"]["native_tracked"] is None
    assert (root / manifest["insert"]["baseline"]["file"]).exists()
    assert (root / manifest["insert"]["expected_final"]["file"]).exists()
    assert (root / manifest["delete"]["baseline"]["file"]).exists()
    assert (root / manifest["delete"]["expected_final"]["file"]).exists()
    assert (root / "NATIVE_ROW_TRACKING_PROBE_INSTRUCTIONS.txt").exists()


def test_v0400_qa_index_does_not_claim_tracked_output(tmp_path: Path):
    root = tmp_path / "qa_hwpx_row_tracking_probe_v0400"
    generate(root)
    index = json.loads((tmp_path / "QA_INDEX_V0400.json").read_text())
    assert index["release"] == "0.40.0-candidate"
    assert index["scenarios"][0]["status"] == "native-oracle-required-fail-closed"


def test_analyzer_exposes_table_geometry_separately_from_text(tmp_path: Path):
    baseline = _table_doc([("A", "1"), ("B", "2")])
    merged = _table_doc([("A", "1"), ("B", "2")])
    # A merge changes physical cell geometry, even with no inserted/deleted row.
    merged.tables[0].cell(0, 0).merge(merged.tables[0].cell(0, 1))
    before_path = tmp_path / "unmerged.hwpx"
    merged_path = tmp_path / "merged.hwpx"
    baseline.save(before_path)
    merged.save(merged_path)
    report = compare_hwpx(before_path, merged_path)
    assert report["delta"]["table_geometry_changed"] is True
    assert "Contents/section0.xml" in report["delta"]["entries_changed"]
    assert report["classification"]["row_specific_revision_anchor_detected"] is False


def test_analyzer_can_compare_hancom_accept_reject_outputs_but_never_self_attests(tmp_path: Path):
    baseline = _table_doc([("A", "1"), ("B", "2")])
    after_insert = _table_doc([("A", "1"), ("X", "9"), ("B", "2")])
    old = tmp_path / "old.hwpx"
    new = tmp_path / "new.hwpx"
    baseline.save(old)
    after_insert.save(new)
    # These plain files are NOT native GUI Accept/Reject evidence. The
    # analyzer should compare snapshots but leave the proof gate closed.
    report = compare_hwpx(old, new, new, accepted=new, rejected=old)
    delta = report["delta"]
    assert delta["accepted_matches_expected_final_text"] is True
    assert delta["accepted_matches_expected_final_geometry"] is True
    assert delta["rejected_matches_baseline_text"] is True
    assert delta["rejected_matches_baseline_geometry"] is True
    assert report["classification"]["native_accept_reject_semantics_verified"] is False
    assert report["classification"]["safe_to_synthesize_row_tracking_from_public_model"] is False


def test_analyzer_finds_unknown_revision_looking_row_attribute_as_candidate(tmp_path: Path):
    from zipfile import ZipFile, ZIP_DEFLATED
    from lxml import etree

    original = tmp_path / "baseline.hwpx"
    altered = tmp_path / "synthetic_candidate.hwpx"
    _table_doc([("A", "1"), ("B", "2")]).save(original)
    with ZipFile(original) as source, ZipFile(altered, "w") as output:
        for entry in source.infolist():
            content = source.read(entry.filename)
            if entry.filename == "Contents/section0.xml":
                root = etree.fromstring(content)
                row = next(node for node in root.iter() if etree.QName(node.tag).localname == "tr")
                # Intentionally synthetic, not an asserted Hancom encoding.
                row.set("rowRevisionId", "999")
                content = etree.tostring(root, encoding="UTF-8", xml_declaration=True)
            output.writestr(entry, content)
    report = compare_hwpx(original, altered)
    assert report["classification"]["row_specific_revision_anchor_detected"] is True
    assert report["classification"]["revision_signal_counts_changed"] is True
    assert any(s["element"] == "tr" for s in report["tracked"]["revision_signals"])
    assert report["classification"]["native_accept_reject_semantics_verified"] is False


def test_oracle_summary_does_not_certify_synthetic_plain_files(tmp_path: Path):
    from tests.quality.verify_native_row_oracle import analyze_scenario

    probe_dir = tmp_path / "probes"
    generate(probe_dir)
    result = analyze_scenario(
        "insert", probe_dir / "row_insert_expected_final_v0400.hwpx", probe_dir,
        accepted=probe_dir / "row_insert_expected_final_v0400.hwpx",
        rejected=probe_dir / "row_insert_probe_base_v0400.hwpx",
    )
    status = result["summary"]
    assert status["machine_snapshot_checks_passed"] is True
    assert status["review_has_track_change_metadata"] is False
    assert status["review_has_revision_signals"] is False
    assert status["row_writer_enablement"] == "BLOCKED"
    assert status["native_gui_provenance_and_review_semantics_confirmed"] is False


@pytest.mark.parametrize("scenario,expected", [
    ("insert", [["A", "1"], ["B", "2"], ["C", "3"], ["", ""]]),
    ("delete", [["A", "1"], ["B", "2"]]),
])
def test_hancom_native_observation_tracks_config_but_not_row_revision(scenario: str, expected: list[list[str]]):
    from tests.quality.verify_native_row_oracle import analyze_scenario
    probe_dir = ROOT / "tests/fixtures/historical/qa_hwpx_row_tracking_probe_v0400"
    observed = probe_dir / "native_observations" / f"user_observed_track_on_{scenario}_unmarked.hwpx"
    result = analyze_scenario(scenario, observed, probe_dir)
    summary = result["summary"]
    delta = result["analysis"]["delta"]
    assert summary["baseline_track_change_config"] == {"flags": "56"}
    assert summary["review_track_change_config"] == {"flags": "57"}
    assert summary["track_change_config_changed"] is True
    assert summary["review_has_tracking_configuration"] is True
    assert summary["review_has_recorded_revisions"] is False
    assert summary["review_has_track_change_metadata"] is False
    assert summary["review_has_revision_signals"] is False
    assert summary["review_has_row_anchor_candidates"] is False
    assert summary["review_geometry_changed"] is True
    assert delta["tracked_row_matrices"] == [expected]
    assert summary["row_writer_enablement"] == "BLOCKED"
