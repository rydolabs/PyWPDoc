"""Offline protection for one-click showcase evidence generation.

No Windows Office is used in this test. Actual screenshots require a user-run
Windows COM export and a separate visual review of the resulting artifacts.
"""
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

from pywpdoc import Document


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tests" / "showcase" / "run_showcase.py"


def test_showcase_runner_creates_two_format_samples_and_uploadable_zip(tmp_path):
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--generate-only",
         "--output-root", str(tmp_path)],
        cwd=ROOT, text=True, capture_output=True, timeout=180,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    results = sorted(tmp_path.glob("SHOWCASE_RESULTS_*.zip"))
    assert len(results) == 1
    with ZipFile(results[0]) as z:
        assert z.testzip() is None
        names = set(z.namelist())
        for fmt in ("docx", "hwpx"):
            for stem in (
                "01_template_before", "02_template_filled",
                "03_revision_before", "04_revision_after",
                "05_tracked_review", "06_preview_before", "07_preview_after",
            ):
                assert f"{stem}.{fmt}" in names
            report = json.loads(z.read(f"preview_report_{fmt}.json"))
            assert report["count"] == 1
            assert b"Acme Corp" in z.read(f"02_template_filled.{fmt}") or (
                "Acme Corp" in Document.open(
                    _extract(z, f"02_template_filled.{fmt}", tmp_path)
                ).paragraphs[-1].text
            )
        summary = json.loads(z.read("results.json"))
        assert summary["package_version"] == "0.44.0"
        assert summary["word"]["status"] == "SKIP"
        assert summary["hancom"]["status"] == "SKIP"
        assert len(summary["scenarios"]) == 6
        assert all(e["status"] == "PASS" for e in summary["scenarios"].values())
        assert "READ_ME_FIRST.txt" in names


def _extract(z: ZipFile, name: str, root: Path) -> Path:
    return Path(z.extract(name, path=root))
