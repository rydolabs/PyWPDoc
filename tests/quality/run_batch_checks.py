"""Run independent PyWPDoc quality gates and retain failure details.

Python tests run to completion even if some tests fail (no --maxfail). The
HWPX native batch analyzer runs independently even if pytest exits nonzero.
This script never automates Hancom GUI interaction or claims its approval UI
was tested.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def _read_junit(path: Path) -> dict:
    tree = ET.parse(path)
    root = tree.getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    failures = []
    counts = {"tests":0, "errors":0, "failures":0, "skipped":0}
    for suite in suites:
        for key in counts:
            counts[key] += int(suite.get(key, "0"))
        for case in suite.findall(".//testcase"):
            for kind in ("failure", "error"):
                for item in case.findall(kind):
                    failures.append({
                        "test":f"{case.get('classname', '')}::{case.get('name', '')}",
                        "kind":kind,
                        "message":item.get("message", ""),
                        "detail":(item.text or "")[-4000:],
                    })
    counts["passed"] = max(0, counts["tests"] - counts["errors"] - counts["failures"] - counts["skipped"])
    return {"counts":counts, "issues":failures}


def run_all(source: Path, output: Path, *, tracked: Path | None = None, skip_python: bool = False) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    reports = {"generated_at":datetime.now(timezone.utc).isoformat(), "gates":{}, "native_batch":None,
               "note":"All executable checks continue independently; native editor GUI semantics are not certified."}
    issues = []
    if not skip_python:
        cmd = [sys.executable, "-m", "pytest", "-q", "--disable-warnings", "--junitxml", str((output / "pytest.xml").resolve())]
        try:
            cp = subprocess.run(cmd, cwd=source, capture_output=True, text=True, timeout=180, check=False)
            (output / "pytest.stdout.log").write_text(cp.stdout, encoding="utf-8")
            (output / "pytest.stderr.log").write_text(cp.stderr, encoding="utf-8")
            details = _read_junit(output / "pytest.xml") if (output / "pytest.xml").exists() else None
            reports["gates"]["python_tests"] = {"status":"PASS" if cp.returncode == 0 else "FAIL",
                                                    "exit_code":cp.returncode, "junit":details}
            if details:
                for issue in details["issues"]:
                    issues.append(f"[PYTEST {issue['kind']}] {issue['test']}: {issue['message']}\n{issue['detail']}")
            if cp.returncode != 0 and not details:
                issues.append(f"[PYTEST ERROR] exit={cp.returncode}\n{cp.stderr[-3000:]}")
        except Exception as exc:
            reports["gates"]["python_tests"] = {"status":"ERROR", "reason":f"{type(exc).__name__}: {exc}"}
            issues.append(f"[PYTEST ERROR] {type(exc).__name__}: {exc}")
    try:
        from tests.quality.native_batch_suite import run_suite
        folder = source / "qa_native_batch_v0400"
        native = run_suite(folder, tracked, output / "native")
        reports["native_batch"] = {
            "status":"ANALYZED" if tracked and tracked.is_file() else "NOT_SUBMITTED",
            "counts":native["counts"],
            "report":str(output / "native" / "results.json"),
        }
        for rec in native["cases"]:
            if rec["status"] != "PASS":
                issues.append(f"[NATIVE {rec['status']}] {rec['id']}: {rec['reason']}")
    except Exception as exc:
        reports["native_batch"] = {"status":"ERROR", "reason":f"{type(exc).__name__}: {exc}"}
        issues.append(f"[NATIVE ERROR] {type(exc).__name__}: {exc}")
    reports["has_automated_failures"] = any(g.get("status") in {"FAIL", "ERROR"} for g in reports["gates"].values())
    (output / "summary.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (output / "issues.log").write_text("\n\n".join(issues)+("\n" if issues else ""), encoding="utf-8")
    lines = ["# PyWPDoc Batch QA Summary", "", "Independent checks continue after failures.", ""]
    for name, value in reports["gates"].items():
        details = value.get("junit") or {}
        counts = details.get("counts", {})
        lines.append(f"- {name}: **{value['status']}**; {counts}")
    nb = reports["native_batch"] or {}
    lines.append(f"- native editor batch: **{nb.get('status')}**; {nb.get('counts', {})}")
    lines.append("- Native GUI Accept/Reject requires human verification; structural revision generation remains blocked.")
    lines.append("\nLogs: `pytest.stdout.log`, `pytest.xml`, `native/results.csv`, `issues.log`.\n")
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, default=ROOT / "qa_batch_results")
    parser.add_argument("--tracked", type=Path, default=None, help="HWPX saved with all native edits, unaccepted")
    parser.add_argument("--skip-python", action="store_true", help="Only analyze the native HWPX")
    args = parser.parse_args()
    result = run_all(args.source.resolve(), args.out.resolve(), tracked=args.tracked, skip_python=args.skip_python)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return int(result["has_automated_failures"])

if __name__ == "__main__":
    raise SystemExit(main())
