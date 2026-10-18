"""Create and inspect one HWPX file containing isolated native-editor probes.

Safety: structural revision support is NEVER inferred from geometry alone.
A diagnostic PASS means a corresponding revision marker was observed in a
locally-edited HWPX, not that Hancom GUI Accept/Reject was independently proved.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from zipfile import ZipFile, BadZipFile

from lxml import etree

from pywpdoc import Document
from pywpdoc._engine import validate_hwpx_file

ROOT = Path(__file__).resolve().parents[1]
SUITE_VERSION = "native-batch-qa/v1"

# First header cell is a persistent case ID; all editing targets are elsewhere.
CASES: tuple[dict[str, Any], ...] = (
    {"id":"T01_INSERT", "kind":"text_insert", "instruction":"본문 2행 오른쪽 셀 ABC 끝에 D 추가 (ABCD)",
     "rows":[["T01_INSERT", "텍스트 삽입"],["TARGET", "ABC"]]},
    {"id":"T02_DELETE", "kind":"text_delete", "instruction":"본문 2행 오른쪽 셀 ABCD에서 마지막 D만 삭제 (ABC)",
     "rows":[["T02_DELETE", "텍스트 삭제"],["TARGET", "ABCD"]]},
    {"id":"T03_REPLACE", "kind":"text_replace", "instruction":"본문 2행 오른쪽 셀 OLD를 NEW로 교체",
     "rows":[["T03_REPLACE", "텍스트 교체"],["TARGET", "OLD"]]},
    {"id":"T04_CHAR", "kind":"char_format", "instruction":"본문 2행 오른쪽 셀 BOLDME 전체를 굵게(Ctrl+B)",
     "rows":[["T04_CHAR", "글자 서식"],["TARGET", "BOLDME"]]},
    {"id":"T05_PARA", "kind":"para_format", "instruction":"본문 2행 오른쪽 셀 ALIGNME 문단 가운데 정렬",
     "rows":[["T05_PARA", "문단 서식"],["TARGET", "ALIGNME"]]},
    {"id":"S06_ROW_INSERT", "kind":"row_insert", "instruction":"A/1 행과 B/2 행 사이에 1행 삽입, 새 행에 X/9 입력",
     "rows":[["S06_ROW_INSERT", "행 삽입"],["A", "1"],["B", "2"],["C", "3"]]},
    {"id":"S07_ROW_DELETE", "kind":"row_delete", "instruction":"B/2 전체 행만 삭제 (표제 행은 유지)",
     "rows":[["S07_ROW_DELETE", "행 삭제"],["A", "1"],["B", "2"],["C", "3"]]},
    {"id":"S08_COL_INSERT", "kind":"col_insert", "instruction":"표 맨 오른쪽에 1열 삽입 (기존 첫 열은 유지)",
     "rows":[["S08_COL_INSERT", "열 삽입"],["A", "1"],["B", "2"]]},
    {"id":"S09_COL_DELETE", "kind":"col_delete", "instruction":"마지막(세 번째) 열 전체 삭제 (첫 열 표제 유지)",
     "rows":[["S09_COL_DELETE", "열 유지", "삭제할 열"],["A", "1", "X"],["B", "2", "Y"]]},
    {"id":"S10_CELL_MERGE", "kind":"cell_merge", "instruction":"표 2행(본문 첫 행)의 오른쪽 두 셀 LEFT와 RIGHT를 병합",
     "rows":[["S10_CELL_MERGE", "병합 대상", "기준"],["M", "LEFT", "RIGHT"],["N", "1", "2"]]},
)
CASE_IDS = {case["id"] for case in CASES}
STRUCTURAL = {"row_insert", "row_delete", "col_insert", "col_delete", "cell_merge"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _local(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.rsplit("}", 1)[-1]


def _table_data(table: etree._Element) -> dict[str, Any]:
    rows = [x for x in table if _local(x.tag) == "tr"]
    texts: list[list[str]] = []
    spans: list[list[dict[str, str]]] = []
    formats: list[list[dict[str, list[str]]]] = []
    for row in rows:
        tc = [x for x in row if _local(x.tag) == "tc"]
        texts.append(["".join(cell.itertext()) for cell in tc])
        spans.append([
            { _local(k): v for k, v in span.attrib.items() }
            if (span := next((x for x in cell if _local(x.tag) == "cellSpan"), None)) is not None
            else {} for cell in tc
        ])
        formats.append([{
            "para_refs": [str(n.get("paraPrIDRef")) for n in cell.iter() if _local(n.tag) == "p"],
            "char_refs": [str(n.get("charPrIDRef")) for n in cell.iter() if _local(n.tag) == "run"],
        } for cell in tc])
    case_id = texts[0][0].strip() if texts and texts[0] else ""
    markers = []
    anchors = []
    candidates = []
    for item in table.iter():
        kind = _local(item.tag)
        if kind in {"insertBegin", "insertEnd", "deleteBegin", "deleteEnd"}:
            markers.append({"kind": kind, "attrs": {_local(k):v for k,v in item.attrib.items()}})
        if kind == "p" and item.get("paraTcId") is not None:
            anchors.append({"kind": "paraTcId", "id": item.get("paraTcId")})
        if kind == "run":
            for attr in ("charTcId", "paraTcId"):
                if item.get(attr) is not None:
                    anchors.append({"kind": attr, "id": item.get(attr)})
        if kind in {"tbl", "tr", "tc"}:
            suspicious = {_local(k):v for k,v in item.attrib.items()
                          if any(s in _local(k).lower() for s in ("revision", "tcid", "track", "change", "insert", "delete"))}
            if suspicious:
                candidates.append({"element":kind, "attrs":suspicious})
            for child in item:
                if any(t in _local(child.tag).lower() for t in ("revision", "track", "change", "insert", "delete")):
                    candidates.append({"element":kind, "child":_local(child.tag)})
    target_markers = []
    target_anchors = []
    # Text/format scenarios only edit the right cell of the second table row.
    # Revisions in headings or unrelated cells cannot satisfy their checks.
    try:
        target_row = rows[1]
        target = [x for x in target_row if _local(x.tag) == "tc"][1]
    except (IndexError, TypeError):
        target = None
    if target is not None:
        for node in target.iter():
            kind = _local(node.tag)
            if kind in {"insertBegin", "insertEnd", "deleteBegin", "deleteEnd"}:
                target_markers.append({"kind": kind, "attrs":{_local(k):v for k,v in node.attrib.items()}})
            if kind == "p" and node.get("paraTcId") is not None:
                target_anchors.append({"kind":"paraTcId", "id":node.get("paraTcId")})
            if kind == "run":
                for attr in ("charTcId", "paraTcId"):
                    if node.get(attr) is not None:
                        target_anchors.append({"kind":attr, "id":node.get(attr)})
    return {
        "id":case_id, "rows":texts, "spans":spans, "formats":formats,
        "target_markers":target_markers, "target_anchors":target_anchors,
        "row_count":len(rows), "col_count":int(table.get("colCnt") or max((len(r) for r in texts), default=0)),
        "markers":markers, "anchors":anchors, "row_revision_candidates":candidates,
    }


def inspect_batch(path: Path) -> dict[str, Any]:
    """Read-only extraction of relevant data from native HWPX (no automatic repair)."""
    tables = {}
    duplicates = set()
    changes = []
    flags = None
    with ZipFile(path) as z:
        names = z.namelist()
        if "Contents/header.xml" not in names:
            raise ValueError("Contents/header.xml is missing")
        header = etree.fromstring(z.read("Contents/header.xml"))
        for node in header.iter():
            kind = _local(node.tag)
            if kind == "trackChange":
                changes.append({ _local(k):v for k,v in node.attrib.items() })
            elif kind == "trackchageConfig":
                flags = node.get("flags")
        for name in sorted(n for n in names if n.startswith("Contents/section") and n.endswith(".xml")):
            root = etree.fromstring(z.read(name))
            for table in root.iter():
                if _local(table.tag) != "tbl":
                    continue
                info = _table_data(table)
                case_id = info["id"]
                if case_id in tables:
                    duplicates.add(case_id)
                tables[case_id] = info
    return {"tables":tables, "duplicates":sorted(duplicates), "track_changes":changes, "track_flags":flags}


def create_suite(folder: Path) -> dict[str, Any]:
    folder.mkdir(parents=True, exist_ok=True)
    doc = Document.new("hwpx")
    doc.add_paragraph("PyWPDoc HWPX Native Batch QA - Track Changes ON")
    doc.add_paragraph("아래 표 10개는 독립 실험입니다. 각 표 첫 칸의 T01/S06 등 식별자는 수정하지 마세요.")
    doc.add_paragraph("검토 > 변경 내용 추적을 켠 뒤 각 표의 지정 작업을 수행하십시오. 승인/거부 없이 다른 이름으로 HWPX 저장.")
    for case in CASES:
        doc.add_paragraph(f"{case['id']} | {case['instruction']}")
        rows = case["rows"]
        table = doc.add_table(len(rows), len(rows[0]), style="Table Grid")
        for i, row in enumerate(rows):
            for j, content in enumerate(row):
                table.cell(i,j).text = content
    target = folder / "01_BATCH_BASE.hwpx"
    doc.save(target)
    valid = validate_hwpx_file(target)
    if not valid.ok:
        raise RuntimeError(f"Generated HWPX failed validation: {valid.issues}")
    inspected = inspect_batch(target)
    if any(cid not in inspected["tables"] for cid in CASE_IDS):
        raise RuntimeError("suite generator missing case anchors")
    manifest = {
        "schema":SUITE_VERSION,
        "project_version":"0.40.0",
        "baseline":"01_BATCH_BASE.hwpx",
        "baseline_sha256":sha256(target),
        "native_review_input":"02_BATCH_TRACKED.hwpx",
        "rules": {"safety":"no structural writer is enabled from these findings", "skip":"unperformed cases are reported, not discarded"},
        "cases":[{"id":c["id"], "kind":c["kind"], "instruction":c["instruction"]} for c in CASES],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    steps = [
        "# 한글 2020 배치 검증 안내", "",
        "1. `01_BATCH_BASE.hwpx`를 한글 2020에서 엽니다.",
        "2. **변경 내용 추적을 켠 다음**, 아래 표를 **각각 독립적으로** 편집합니다.",
        "3. 문제가 발생한 표는 그대로 두고 **다음 표**로 넘어갑니다. 첫 칸의 T01/S06 식별자는 건드리지 않습니다.",
        "4. 변경 내용을 승인하거나 거부하지 말고 `02_BATCH_TRACKED.hwpx`라는 이름으로 **HWPX 저장**합니다.",
        "5. `02_BATCH_TRACKED.hwpx` **한 파일만 업로드**하면 나머지는 제가 일괄 분석합니다.",
        "6. 선택 사항: 같은 파일에서 '모두 승인'/'모두 거부'를 각각 복사 저장하면 후속 GUI 판정을 추가할 수 있습니다.",
        "", "## 실험 10개", "",
        "| ID | 표에서 수행할 작업 |", "|---|---|",
        *[f"| {c['id']} | {c['instruction']} |" for c in CASES],
        "", "## 판정의 한계", "",
        "HWPX 파일에서 변경 이력이 탐지돼도 **한글 GUI의 승인/거부 의미까지 자동으로 검증되지는 않습니다.**",
        "행/열 삽입·삭제 및 병합은 실제 구조 변경과 revision 앵커를 별도로 검사하며, 구조 변화만으로 변경 추적이 지원된다고 판정하지 않습니다.",
        "텍스트 변경은 구체적인 마커/메타데이터를 판정하고, 서식 변경은 해당 표의 paraTcId/charTcId 앵커를 확인합니다.",
        "", "## 독립 실행 로그", "",
        "`python -m quality.native_batch_suite run --suite native_batch_suite --tracked 02_BATCH_TRACKED.hwpx --out qa_results`",
        "명령을 실행하면 JSON, CSV, Markdown, issues.log를 생성합니다. HWPX가 아직 없으면 모든 항목을 SKIP으로 보고합니다.",
    ]
    (folder / "INSTRUCTIONS_KO.md").write_text("\n".join(steps)+"\n", encoding="utf-8")
    return manifest


def _linked_marker_pair(markers: list[dict[str, Any]], changes: list[dict[str, str]], kind: str) -> bool:
    """Find a begin/end range sharing IDs and linked to matching metadata."""
    entries = {change.get("id") for change in changes if change.get("type") == kind}
    starts = {"Insert": "insertBegin", "Delete": "deleteBegin"}
    start = starts[kind]
    end = {"Insert": "insertEnd", "Delete": "deleteEnd"}[kind]
    for begin in (m for m in markers if m["kind"] == start):
        attrs = begin.get("attrs", {})
        if not attrs.get("TcId") or attrs.get("TcId") not in entries:
            continue
        for finish in (m for m in markers if m["kind"] == end):
            final = finish.get("attrs", {})
            if attrs.get("Id") == final.get("Id") and attrs.get("TcId") == final.get("TcId"):
                return True
    return False


def _linked_format_anchor(anchors: list[dict[str, Any]], changes: list[dict[str, str]], kind: str) -> bool:
    attr = "charTcId" if kind == "CharShape" else "paraTcId"
    known = {c.get("id") for c in changes if c.get("type") == kind}
    return any(a["kind"] == attr and a.get("id") in known for a in anchors)


def evaluate_case(case: dict[str, Any], base: dict[str, Any], result: dict[str, Any], changes: list[dict[str, str]]) -> dict[str, Any]:
    before = base["tables"].get(case["id"])
    after = result["tables"].get(case["id"])
    if before is None:
        raise ValueError("manifest's baseline case ID is missing")
    if after is None:
        raise ValueError("case header ID missing in edited document; may have been deleted/edited")
    if case["id"] in result.get("duplicates", []):
        raise ValueError("duplicate case ID in edited document; cannot uniquely attribute results")
    kind = case["kind"]
    marker_types = {m["kind"] for m in after["markers"]}
    anchor_types = {a["kind"] for a in after["anchors"]}
    target_marker_types = {m["kind"] for m in after["target_markers"]}
    target_anchor_types = {a["kind"] for a in after["target_anchors"]}
    meta = {entry.get("type", "") for entry in changes}
    target_changed = before["rows"] != after["rows"]
    geometry_changed = (before["row_count"] != after["row_count"]
        or before["col_count"] != after["col_count"] or before["spans"] != after["spans"])
    fields = {
        "id":case["id"], "kind":kind, "status":"SKIP", "reason":"", "observed_change": target_changed or geometry_changed,
        "marker_types":sorted(marker_types), "anchor_types":sorted(anchor_types),
        "target_marker_types":sorted(target_marker_types), "target_anchor_types":sorted(target_anchor_types),
        "revision_candidates":after["row_revision_candidates"],
        "before_rows":before["row_count"], "after_rows":after["row_count"],
        "before_cols":before["col_count"], "after_cols":after["col_count"],
        "header_revision_types":sorted(meta),
        "review_semantics_verified":False,
    }
    if kind in STRUCTURAL:
        if kind == "row_insert":
            changed = after["row_count"] > before["row_count"]
        elif kind == "row_delete":
            changed = after["row_count"] < before["row_count"]
        elif kind == "col_insert":
            changed = after["col_count"] > before["col_count"]
        elif kind == "col_delete":
            changed = after["col_count"] < before["col_count"]
        else:
            changed = before["spans"] != after["spans"]
        fields["observed_change"] = changed
        if not changed:
            fields["status"] = "SKIP"
            fields["reason"] = "requested structural operation not detected"
        elif after["row_revision_candidates"]:
            fields["status"] = "REVIEW"
            fields["reason"] = "structural revision-like anchor found; native row/column semantics not verified"
        else:
            fields["status"] = "UNTRACKED"
            fields["reason"] = ("structural change with only text/format anchors (not row/column tracking)"
                                if marker_types or anchor_types else
                                "structural change detected with no local revision anchors")
    else:
        expected = {
            "text_insert": ({"insertBegin", "insertEnd"}, {"Insert"}),
            "text_delete": ({"deleteBegin", "deleteEnd"}, {"Delete"}),
            "text_replace": ({"insertBegin", "insertEnd", "deleteBegin", "deleteEnd"}, {"Insert", "Delete"}),
        }
        if kind in expected:
            # All ranges must resolve to the correct header change ID; unrelated
            # revisions in other cases cannot satisfy this one.
            required_types = {"text_insert": ("Insert",), "text_delete": ("Delete",),
                              "text_replace": ("Insert", "Delete")}[kind]
            matched = all(_linked_marker_pair(after["target_markers"], changes, item) for item in required_types)
            if matched:
                fields["status"] = "PASS"
                fields["reason"] = "local begin/end range IDs match the corresponding header change IDs"
            elif target_changed or marker_types:
                fields["status"] = "FAIL"
                fields["reason"] = "content changed, but linked local revision ranges are absent or incomplete"
            else:
                fields["status"] = "SKIP"
                fields["reason"] = "text edit not detected"
        else:
            fmt = "CharShape" if kind == "char_format" else "ParaShape"
            anchor_ok = _linked_format_anchor(after["target_anchors"], changes, fmt)
            if anchor_ok:
                fields["status"] = "PASS"
                fields["reason"] = "local format revision anchor references matching header change ID"
            elif ("charTcId" in target_anchor_types or "paraTcId" in target_anchor_types):
                fields["status"] = "REVIEW"
                fields["reason"] = "revision anchor found, but header change ID/type does not match"
            else:
                # Check the target cell's paragraph/run formatting refs. This
                # can detect a plain format edit without falsely calling it a
                # recorded revision. Metadata-only edits may remain SKIP.
                selector = "char_refs" if kind == "char_format" else "para_refs"
                try:
                    before_refs = before["formats"][1][1][selector]
                    after_refs = after["formats"][1][1][selector]
                    changed_format = before_refs != after_refs
                except (IndexError, KeyError):
                    changed_format = False
                fields["observed_change"] = changed_format
                if changed_format:
                    fields["status"] = "FAIL"
                    fields["reason"] = "format refs changed, but no linked revision anchor was found"
                else:
                    fields["status"] = "SKIP"
                    fields["reason"] = "format revision anchor or format-reference change not detected"
    return fields


def run_suite(suite: Path, tracked: Path | None, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    problems = []
    manifest_file = suite / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    baseline = suite / manifest["baseline"]
    if sha256(baseline) != manifest["baseline_sha256"]:
        raise ValueError("baseline sha256 differs from suite manifest (do not modify 01_BATCH_BASE.hwpx)")
    base = inspect_batch(baseline)
    edited = None
    input_error = None
    if tracked is None or not tracked.is_file():
        input_error = "no edited HWPX supplied"
    else:
        try:
            edited = inspect_batch(tracked)
        except (BadZipFile, OSError, ValueError, etree.XMLSyntaxError, KeyError) as exc:
            input_error = f"could not open/parse edited HWPX: {type(exc).__name__}: {exc}"
    results = []
    for case in manifest["cases"]:
        try:
            if edited is None:
                status = "SKIP" if tracked is None or not tracked.is_file() else "ERROR"
                record = {"id":case["id"], "kind":case["kind"], "status":status, "reason":input_error, "review_semantics_verified":False}
            else:
                record = evaluate_case(case, base, edited, edited["track_changes"])
        except Exception as exc:  # deliberate per-case error boundary
            record = {"id":case["id"], "kind":case["kind"], "status":"ERROR", "reason":f"{type(exc).__name__}: {exc}", "review_semantics_verified":False}
        results.append(record)
        if record["status"] != "PASS":
            problems.append(f"{record['id']} [{record['status']}]: {record['reason']}")
    counts = dict(sorted(Counter(item["status"] for item in results).items()))
    payload = {
        "schema":SUITE_VERSION, "generated_at":datetime.now(timezone.utc).isoformat(),
        "baseline":str(baseline), "tracked":str(tracked) if tracked else None,
        "tracking_config_baseline":base["track_flags"],
        "tracking_config_edited":edited["track_flags"] if edited else None,
        "metadata_change_types":sorted({c.get("type", "") for c in edited["track_changes"]}) if edited else [],
        "caveat":"PASS = file-format evidence only; GUI accept/reject is NOT verified. Structural writer remains BLOCKED.",
        "counts":counts, "cases":results, "input_error":input_error,
    }
    (output / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    with (output / "results.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        columns = ["id", "kind", "status", "observed_change", "reason", "before_rows", "after_rows", "before_cols", "after_cols"]
        wr = csv.DictWriter(fp, fieldnames=columns, extrasaction="ignore")
        wr.writeheader()
        wr.writerows(results)
    lines = ["# 한글 2020 일괄 검증 결과", "", f"- 결과: {json.dumps(counts, ensure_ascii=False)}",
             f"- 변경 추적 설정: {base['track_flags']} → {edited['track_flags'] if edited else '(미입력)'}",
             "- `PASS`는 HWPX 안의 마커 증거만 의미하며 GUI 승인·거부 성공 판정이 아닙니다.",
             "- 표 구조 변경 추적 쓰기 기능은 계속 **미지원(fail-closed)** 입니다.",
             "", "| ID | 상태 | 판정 사유 |", "|---|---|---|"]
    for rec in results:
        reason = str(rec.get("reason", "")).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {rec['id']} | {rec['status']} | {reason} |")
    (output / "results.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    (output / "issues.log").write_text("\n".join(problems)+("\n" if problems else ""), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="create a unified native-editor HWPX exercise")
    g.add_argument("--out", type=Path, default=ROOT / "tests/fixtures/historical/qa_native_batch_v0400")
    r = sub.add_parser("run", help="analyze all cases, always record per-case errors")
    r.add_argument("--suite", type=Path, default=ROOT / "tests/fixtures/historical/qa_native_batch_v0400")
    r.add_argument("--tracked", type=Path)
    r.add_argument("--out", type=Path, default=ROOT / "tests/fixtures/historical/qa_native_batch_v0400" / "results")
    args = parser.parse_args()
    if args.cmd == "generate":
        summary = create_suite(args.out)
        print(f"created {len(summary['cases'])} cases: {args.out}")
    else:
        report = run_suite(args.suite, args.tracked, args.out)
        print(json.dumps(report["counts"], ensure_ascii=False))
        print(f"saved reports to {args.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
