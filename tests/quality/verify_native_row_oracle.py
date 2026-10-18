"""Summarize structural evidence from a Hancom-authored row Track Changes probe.

This script never certifies Hancom provenance or Accept/Reject behavior.
Those must be observed in the native editor and recorded by the operator.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.quality.analyze_hwpx_row_tracking import compare_hwpx

PROBES = {
    "insert": ("row_insert_probe_base_v0400.hwpx", "row_insert_expected_final_v0400.hwpx"),
    "delete": ("row_delete_probe_base_v0400.hwpx", "row_delete_expected_final_v0400.hwpx"),
}


def analyze_scenario(
    scenario: str,
    tracked: str | Path,
    probe_dir: str | Path,
    *,
    accepted: str | Path | None = None,
    rejected: str | Path | None = None,
) -> dict:
    """Analyze files and return a compact verdict plus the full diagnostic."""
    if scenario not in PROBES:
        raise ValueError(f"unknown scenario {scenario!r}")
    baseline_name, final_name = PROBES[scenario]
    report = compare_hwpx(
        Path(probe_dir) / baseline_name, tracked,
        Path(probe_dir) / final_name, accepted, rejected,
    )
    delta = report["delta"]
    classification = report["classification"]
    native_revision_metadata = bool(report["tracked"]["track_changes"])
    native_revision_signals = bool(report["tracked"]["revision_signals"])
    snapshots_match = (
        delta.get("accepted_matches_expected_final_text") is True
        and delta.get("accepted_matches_expected_final_geometry") is True
        and delta.get("rejected_matches_baseline_text") is True
        and delta.get("rejected_matches_baseline_geometry") is True
    )
    summary = {
        "scenario": scenario,
        "review_has_track_change_metadata": native_revision_metadata,
        "review_has_tracking_configuration": report["tracked"]["track_change_config"] is not None,
        "baseline_track_change_config": report["baseline"]["track_change_config"],
        "review_track_change_config": report["tracked"]["track_change_config"],
        "track_change_config_changed": delta["track_change_config_changed"],
        "review_has_recorded_revisions": bool(
            native_revision_metadata or native_revision_signals
            or report["tracked"]["inline_markers"]
            or report["tracked"]["paragraph_or_run_revision_anchors"]
            or report["tracked"]["row_revision_anchor_candidates"]
        ),
        "review_has_revision_signals": native_revision_signals,
        "review_has_row_anchor_candidates": classification["row_specific_revision_anchor_detected"],
        "review_geometry_changed": delta["table_geometry_changed"],
        "review_matches_expected_final_text": delta.get("tracked_matches_expected_final_structure"),
        "accept_snapshot_matches_expected_final": (
            delta.get("accepted_matches_expected_final_text") is True
            and delta.get("accepted_matches_expected_final_geometry") is True
        ) if accepted is not None else None,
        "reject_snapshot_matches_baseline": (
            delta.get("rejected_matches_baseline_text") is True
            and delta.get("rejected_matches_baseline_geometry") is True
        ) if rejected is not None else None,
        "machine_snapshot_checks_passed": snapshots_match,
        "native_gui_provenance_and_review_semantics_confirmed": False,
        "row_writer_enablement": "BLOCKED",
    }
    if not summary["review_has_recorded_revisions"] and delta["track_change_config_changed"]:
        summary["next_action"] = (
            "Tracking configuration changed but no recorded revisions were found. "
            "Check one simple text edit in Hancom with tracking on to distinguish "
            "unsupported row tracking from a recording/saving issue."
        )
    elif not summary["review_has_recorded_revisions"]:
        summary["next_action"] = "No detected revision signals: check Hancom GUI tracking and whether row operations are tracked."
    elif accepted is None or rejected is None:
        summary["next_action"] = "Save separate Hancom Accept All / Reject All copies, then rerun with --accepted and --rejected."
    elif not snapshots_match:
        summary["next_action"] = "Investigate mismatch between GUI Accept/Reject outputs and baseline/expected-final snapshots."
    else:
        summary["next_action"] = "Manually verify editor provenance, row-level review UI, and revision-anchor semantics before implementing a writer."
    return {"summary": summary, "analysis": report}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=sorted(PROBES))
    parser.add_argument("tracked", type=Path, help="Native HWPX saved BEFORE accepting/rejecting")
    parser.add_argument("--probe-dir", type=Path, default=ROOT / "tests/fixtures/historical/qa_hwpx_row_tracking_probe_v0400")
    parser.add_argument("--accepted", type=Path, help="Native Accept All saved copy")
    parser.add_argument("--rejected", type=Path, help="Native Reject All saved copy")
    parser.add_argument("--output", type=Path, help="Save full JSON analysis")
    args = parser.parse_args()
    payload = analyze_scenario(
        args.scenario, args.tracked, args.probe_dir,
        accepted=args.accepted, rejected=args.rejected,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
