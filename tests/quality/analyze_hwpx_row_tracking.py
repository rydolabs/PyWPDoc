"""Inspect HWPX table-row changes and revision signals.

This tool is intentionally read-only.  It is designed for comparing a plain
baseline HWPX with a Hancom-authored file saved while Track Changes was on.
It does not assume that table-row changes have a verified HWPX encoding.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter
from typing import Any
from zipfile import ZipFile

from lxml import etree


def _local(tag: Any) -> str:
    try:
        return etree.QName(tag).localname
    except Exception:
        return str(tag).split("}")[-1]


def _attrs(node: etree._Element) -> dict[str, str]:
    return {_local(k): v for k, v in node.attrib.items()}


def _text(node: etree._Element) -> str:
    return "".join(node.itertext())


def _ancestor(node: etree._Element, name: str) -> etree._Element | None:
    cur = node.getparent()
    while cur is not None:
        if _local(cur.tag) == name:
            return cur
        cur = cur.getparent()
    return None


def _cell_location(node: etree._Element) -> dict[str, Any] | None:
    tc = _ancestor(node, "tc")
    if tc is None:
        return None
    addr = next((c for c in tc if _local(c.tag) == "cellAddr"), None)
    out: dict[str, Any] = {}
    if addr is not None:
        out.update({k: int(v) if v.isdigit() else v for k, v in _attrs(addr).items()})
    tr = _ancestor(tc, "tr")
    tbl = _ancestor(tc, "tbl")
    if tr is not None and tbl is not None:
        rows = [c for c in tbl if _local(c.tag) == "tr"]
        try:
            out["physical_row_index"] = rows.index(tr)
        except ValueError:
            pass
    if tbl is not None:
        out["table_id"] = tbl.get("id")
    return out


def _table_snapshot(root: etree._Element) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    for table_index, tbl in enumerate(n for n in root.iter() if _local(n.tag) == "tbl"):
        rows_out: list[dict[str, Any]] = []
        rows = [c for c in tbl if _local(c.tag) == "tr"]
        for row_index, tr in enumerate(rows):
            cells_out: list[dict[str, Any]] = []
            for tc in (c for c in tr if _local(c.tag) == "tc"):
                addr = next((c for c in tc if _local(c.tag) == "cellAddr"), None)
                span = next((c for c in tc if _local(c.tag) == "cellSpan"), None)
                cell = {
                    "text": _text(tc),
                    "attrs": _attrs(tc),
                    "cellAddr": _attrs(addr) if addr is not None else None,
                    "cellSpan": _attrs(span) if span is not None else None,
                }
                cells_out.append(cell)
            rows_out.append({"row_index": row_index, "attrs": _attrs(tr), "cells": cells_out})
        tables.append({
            "table_index": table_index,
            "attrs": _attrs(tbl),
            "declared_row_count": tbl.get("rowCnt"),
            "declared_col_count": tbl.get("colCnt"),
            "actual_row_count": len(rows),
            "rows": rows_out,
        })
    return tables


def _table_geometry(info: dict[str, Any]) -> list[dict[str, Any]]:
    """Describe table geometry without conflating cell text with row structure."""
    geometry: list[dict[str, Any]] = []
    for section in info["sections"]:
        for table in section["tables"]:
            geometry.append({
                "section": section["name"],
                "declared_row_count": table["declared_row_count"],
                "declared_col_count": table["declared_col_count"],
                "actual_row_count": table["actual_row_count"],
                "rows": [
                    [{"cellAddr": cell["cellAddr"], "cellSpan": cell["cellSpan"]}
                     for cell in row["cells"]]
                    for row in table["rows"]
                ],
            })
    return geometry


def _revision_signals(root: etree._Element, section_name: str) -> list[dict[str, Any]]:
    """Enumerate *candidate* revision signals anywhere in a section.

    Unknown Hancom row encodings must not be hidden by assuming that all
    revisions use the familiar text-range or paragraph/run element names.
    A signal is diagnostic, not evidence of Accept/Reject semantics.
    """
    tokens = ("tcid", "track", "change", "revision", "insert", "delete")
    signals: list[dict[str, Any]] = []
    for node in root.iter():
        name = _local(node.tag)
        relevant_attrs = {k: v for k, v in _attrs(node).items()
                          if any(token in k.lower() for token in tokens)}
        if not (any(token in name.lower() for token in tokens) or relevant_attrs):
            continue
        parent = node.getparent()
        row = _ancestor(node, "tr")
        table = _ancestor(node, "tbl")
        signals.append({
            "section": section_name,
            "element": name,
            "parent": _local(parent.tag) if parent is not None else None,
            "attributes": relevant_attrs,
            "inside_table": table is not None,
            "inside_row": row is not None,
            "cell": _cell_location(node),
        })
    return signals


def _signal_counts(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter((s["element"], s["parent"], s["inside_table"])
                     for s in signals)
    return [
        {"element": element, "parent": parent, "inside_table": inside_table, "count": count}
        for (element, parent, inside_table), count in sorted(
            counts.items(), key=lambda item: (item[0][0], item[0][1] or "", item[0][2])
        )
    ]


def _marker_snapshot(root: etree._Element, section_name: str) -> list[dict[str, Any]]:
    names = {"insertBegin", "insertEnd", "deleteBegin", "deleteEnd"}
    result: list[dict[str, Any]] = []
    for node in root.iter():
        name = _local(node.tag)
        if name not in names:
            continue
        parent = node.getparent()
        p = _ancestor(node, "p")
        result.append({
            "section": section_name,
            "kind": name,
            "attrs": _attrs(node),
            "parent": _local(parent.tag) if parent is not None else None,
            "paragraph_id": p.get("id") if p is not None else None,
            "cell": _cell_location(node),
        })
    return result


def _paragraph_revision_anchors(root: etree._Element, section_name: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for node in root.iter():
        name = _local(node.tag)
        if name == "p" and node.get("paraTcId") is not None:
            out.append({"section": section_name, "kind": "paraTcId", "value": node.get("paraTcId"), "cell": _cell_location(node)})
        if name == "run":
            for attr in ("charTcId", "paraTcId"):
                if node.get(attr) is not None:
                    out.append({"section": section_name, "kind": f"run@{attr}", "value": node.get(attr), "cell": _cell_location(node)})
    return out


def _row_anchor_candidates(root: etree._Element, section_name: str) -> list[dict[str, Any]]:
    """Return revision-looking state directly attached to tbl/tr/tc nodes.

    Text markers inside cell paragraphs are deliberately excluded: those prove
    text-range tracking, not a row-structural anchor.
    """
    out: list[dict[str, Any]] = []
    tokens = ("tcid", "track", "change", "revision", "insert", "delete")
    for node in root.iter():
        name = _local(node.tag)
        if name not in {"tbl", "tr", "tc"}:
            continue
        suspicious = {k: v for k, v in _attrs(node).items() if any(t in k.lower() for t in tokens)}
        if suspicious:
            out.append({"section": section_name, "element": name, "attrs": suspicious})
        for child in node:
            child_name = _local(child.tag)
            if any(t in child_name.lower() for t in tokens):
                out.append({"section": section_name, "element": name, "child": child_name, "attrs": _attrs(child)})
    return out


def inspect_hwpx(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with ZipFile(path) as zf:
        names = zf.namelist()
        # Retain fingerprints for the entire package, including non-standard
        # revision/history parts and changed auxiliary metadata.
        fingerprints = {
            name: hashlib.sha256(zf.read(name)).hexdigest()
            for name in names if not name.endswith("/")
        }
        header_name = "Contents/header.xml"
        header = etree.fromstring(zf.read(header_name)) if header_name in names else None
        track_changes: list[dict[str, str]] = []
        authors: list[dict[str, str]] = []
        track_config: dict[str, str] | None = None
        if header is not None:
            for node in header.iter():
                name = _local(node.tag)
                if name == "trackChange":
                    track_changes.append(_attrs(node))
                elif name == "trackChangeAuthor":
                    authors.append(_attrs(node))
                elif name == "trackchageConfig":
                    track_config = _attrs(node)

        sections: list[dict[str, Any]] = []
        all_markers: list[dict[str, Any]] = []
        all_para_anchors: list[dict[str, Any]] = []
        all_row_candidates: list[dict[str, Any]] = []
        all_revision_signals: list[dict[str, Any]] = []
        for name in sorted(n for n in names if n.startswith("Contents/section") and n.endswith(".xml")):
            root = etree.fromstring(zf.read(name))
            tables = _table_snapshot(root)
            markers = _marker_snapshot(root, name)
            para_anchors = _paragraph_revision_anchors(root, name)
            row_candidates = _row_anchor_candidates(root, name)
            revision_signals = _revision_signals(root, name)
            sections.append({"name": name, "tables": tables})
            all_markers.extend(markers)
            all_para_anchors.extend(para_anchors)
            all_row_candidates.extend(row_candidates)
            all_revision_signals.extend(revision_signals)

        history_parts = [n for n in names if any(token in n.lower() for token in ("history", "versionlog", "version_log", "historylog"))]
        version_attrs: dict[str, str] | None = None
        if "version.xml" in names:
            version_attrs = _attrs(etree.fromstring(zf.read("version.xml")))

    return {
        "path": str(path),
        "entries": names,
        "entry_sha256": fingerprints,
        "version": version_attrs,
        "track_changes": track_changes,
        "track_change_authors": authors,
        "track_change_config": track_config,
        "inline_markers": all_markers,
        "paragraph_or_run_revision_anchors": all_para_anchors,
        "row_revision_anchor_candidates": all_row_candidates,
        "revision_signals": all_revision_signals,
        "revision_signal_counts": _signal_counts(all_revision_signals),
        "history_parts": history_parts,
        "sections": sections,
    }


def _row_matrices(info: dict[str, Any]) -> list[list[list[str]]]:
    matrices: list[list[list[str]]] = []
    for section in info["sections"]:
        for table in section["tables"]:
            matrix: list[list[str]] = []
            for row in table["rows"]:
                matrix.append([cell["text"] for cell in row["cells"]])
            matrices.append(matrix)
    return matrices


def compare_hwpx(
    baseline: str | Path, tracked: str | Path, expected_final: str | Path | None = None,
    accepted: str | Path | None = None, rejected: str | Path | None = None,
) -> dict[str, Any]:
    base = inspect_hwpx(baseline)
    review = inspect_hwpx(tracked)
    base_entries = set(base["entries"])
    review_entries = set(review["entries"])
    report: dict[str, Any] = {
        "baseline": base,
        "tracked": review,
        "delta": {
            "entries_added": sorted(review_entries - base_entries),
            "entries_removed": sorted(base_entries - review_entries),
            "entries_changed": sorted(
                name for name in base_entries & review_entries
                if base["entry_sha256"].get(name) != review["entry_sha256"].get(name)
            ),
            "baseline_row_matrices": _row_matrices(base),
            "tracked_row_matrices": _row_matrices(review),
            "baseline_geometry": _table_geometry(base),
            "tracked_geometry": _table_geometry(review),
            "baseline_track_change_config": base["track_change_config"],
            "tracked_track_change_config": review["track_change_config"],
            "track_change_config_changed": base["track_change_config"] != review["track_change_config"],
            "baseline_revision_signal_counts": base["revision_signal_counts"],
            "tracked_revision_signal_counts": review["revision_signal_counts"],
        },
    }
    # Legacy key is retained for v0.40.0 report compatibility; it includes
    # cell-text differences. The geometry key detects actual table-structure
    # differences even when all cell text remains unchanged.
    report["delta"]["structure_changed"] = report["delta"]["baseline_row_matrices"] != report["delta"]["tracked_row_matrices"]
    report["delta"]["table_geometry_changed"] = report["delta"]["baseline_geometry"] != report["delta"]["tracked_geometry"]
    report["delta"]["revision_signal_counts_changed"] = report["delta"]["baseline_revision_signal_counts"] != report["delta"]["tracked_revision_signal_counts"]
    if expected_final is not None:
        final = inspect_hwpx(expected_final)
        report["expected_final"] = final
        report["delta"]["tracked_matches_expected_final_structure"] = _row_matrices(review) == _row_matrices(final)
        report["delta"]["tracked_matches_expected_final_geometry"] = _table_geometry(review) == _table_geometry(final)
    if accepted is not None:
        accept_info = inspect_hwpx(accepted)
        report["accepted"] = accept_info
        report["delta"]["accepted_matches_expected_final_text"] = (
            _row_matrices(accept_info) == _row_matrices(report["expected_final"])
            if expected_final is not None else None
        )
        report["delta"]["accepted_matches_expected_final_geometry"] = (
            _table_geometry(accept_info) == _table_geometry(report["expected_final"])
            if expected_final is not None else None
        )
    if rejected is not None:
        reject_info = inspect_hwpx(rejected)
        report["rejected"] = reject_info
        report["delta"]["rejected_matches_baseline_text"] = _row_matrices(reject_info) == _row_matrices(base)
        report["delta"]["rejected_matches_baseline_geometry"] = _table_geometry(reject_info) == _table_geometry(base)

    marker_parents = sorted({m.get("parent") for m in review["inline_markers"] if m.get("parent")})
    report["classification"] = {
        "track_change_types": sorted({c.get("type", "") for c in review["track_changes"] if c.get("type")}),
        "inline_text_tracking_detected": bool(review["inline_markers"]),
        "inline_marker_parents": marker_parents,
        "markers_inside_table_cells": sum(1 for m in review["inline_markers"] if m.get("cell") is not None),
        "paragraph_or_run_revision_anchors_detected": bool(review["paragraph_or_run_revision_anchors"]),
        "row_specific_revision_anchor_detected": bool(review["row_revision_anchor_candidates"]),
        "revision_signal_counts": review["revision_signal_counts"],
        "revision_signal_counts_changed": report["delta"]["revision_signal_counts_changed"],
        "history_parts_detected": bool(review["history_parts"]),
        "safe_to_synthesize_row_tracking_from_public_model": False,
        "native_accept_reject_semantics_verified": False,
        "native_accept_reject_semantics_note": (
            "Snapshot equivalence is machine-checkable, but provenance and Hancom GUI Accept All / Reject All "
            "operations require independent human confirmation."
        ),
        "reason": (
            "Hancom's public OWPML model exposes Insert/Delete markers as hp:t mixed-content and verified format anchors on paragraph/run; "
            "no hp:tr-specific Track Changes anchor is established by this analyzer. A Hancom-authored row-change sample is required before synthesis."
        ),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("tracked", type=Path)
    parser.add_argument("--expected-final", type=Path)
    parser.add_argument("--accepted", type=Path, help="Hancom Accept All output, never synthesized")
    parser.add_argument("--rejected", type=Path, help="Hancom Reject All output, never synthesized")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = compare_hwpx(args.baseline, args.tracked, args.expected_final, args.accepted, args.rejected)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
