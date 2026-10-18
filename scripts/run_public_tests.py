"""Run the public, redistributable-fixture CI subset.

The historical 709 tests were run with a real externally authored school
announcement. We do not ship that document, or the tests requiring it, in
public CI without redistribution permission. This exclusion is explicit.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EXCLUDED_CASES = (
    "tests/test_docx_quality_gate_v0260.py::test_school_notice_conversion_passes_opc_gate_and_keeps_baseline_parts",
    "tests/test_find_feature_v0230.py::test_find_is_read_only_for_v0215_hwpx_golden",
    "tests/test_find_feature_v0230.py::test_find_is_read_only_for_docx_package_parts",
    "tests/test_replace_feature_v0240.py::test_replace_noop_preserves_v0215_hwpx_golden",
    "tests/test_replace_feature_v0240.py::test_replace_noop_preserves_docx_package_parts",
    "tests/test_replace_feature_v0240.py::test_replace_real_hwpx_changes_only_section_content_part",
    "tests/test_replace_feature_v0240.py::test_replace_real_docx_keeps_unrelated_selected_parts_stable",
    "tests/test_replace_preview_v0420.py::test_original_hwpx_archive_is_unchanged_after_preview_and_resave",
    "tests/test_replace_preview_v0420.py::test_rebuilt_docx_archive_is_unchanged_after_preview_and_resave",
    "tests/test_template_feature_v0250.py::test_template_noop_preserves_v0215_hwpx_golden",
    "tests/test_template_feature_v0250.py::test_template_noop_preserves_docx_package_parts",
    "tests/test_template_sections_v0280.py::test_sections_true_noop_preserves_v0215_hwpx_golden",
    "tests/test_template_sections_v0280.py::test_sections_true_noop_preserves_docx_selected_parts",
)
EXCLUDED_FILES = (
    "tests/test_roundtrip.py",  # immutable school notice HWPX source
    "tests/test_baseline_manifest_v0220.py",  # exact private fixture hash
    "tests/test_hwpx_compatibility_v0341.py",  # private source document
    "tests/test_pywpdoc_namespace_v0220.py",  # private source document
)
if __name__ == "__main__":
    missing = ROOT / "tests/fixtures/original_notice.hwpx"
    if missing.exists():
        print("PUBLIC TEST WARNING: private fixture exists; public selector still excludes its dependent tests")
    args = ["-q", *["--ignore=" + f for f in EXCLUDED_FILES], *["--deselect=" + c for c in EXCLUDED_CASES], *sys.argv[1:]]
    print(f"Public test exclusions: {', '.join(EXCLUDED_FILES)}",flush=True)
    sys.exit(pytest.main(args))
