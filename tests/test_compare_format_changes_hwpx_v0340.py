"""v0.34.2 HWPX formatting Track Changes safety rollback.

Hancom 2020 GUI testing proved that the v0.34.0/v0.34.1 synthesized
CharShape/ParaShape anchors were not recognized as actual formatting revisions.
This historical safety rollback is superseded for CharShape in v0.34.4 and
ParaShape in v0.36.0; the remaining tests preserve mutation and style guards.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pywpdoc import Document, DocumentUnsupportedError
from pywpdoc.features.compare import build_revision_plan
from pywpdoc._engine import validate_hwpx_file


def _one_para(text: str = "Alpha Beta") -> tuple[Document, Document]:
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    old.add_paragraph(text)
    new.add_paragraph(text)
    return old, new


def _snapshot(doc: Document):
    native = doc.backend.native
    return (native.header_model.to_dict(), tuple(section.to_dict() for section in native.section_models))


def _assert_paragraph_format_supported(old: Document, new: Document, tmp_path: Path) -> None:
    old_before = _snapshot(old)
    new_before = _snapshot(new)
    out = tmp_path / "paragraph-format.hwpx"
    old.compare(new, author="Format QA", date="2026-10-09T00:00:00Z", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    assert _snapshot(old) == old_before
    assert _snapshot(new) == new_before


def test_hwpx_run_format_change_is_supported_without_mutating_inputs(tmp_path: Path):
    old, new = _one_para()
    new.paragraphs[0].runs[0].bold = True
    plan = build_revision_plan(old, new, everywhere=False)
    assert len(plan.run_formats) == 1
    old_before = _snapshot(old)
    new_before = _snapshot(new)
    out = tmp_path / "run-format.hwpx"
    old.compare(new, author="Format QA", date="2026-10-09T00:00:00Z", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    assert _snapshot(old) == old_before
    assert _snapshot(new) == new_before


def test_hwpx_font_size_change_is_supported_without_mutating_inputs(tmp_path: Path):
    old, new = _one_para()
    new.paragraphs[0].runs[0].font.size = 14
    plan = build_revision_plan(old, new, everywhere=False)
    assert len(plan.run_formats) == 1
    old_before = _snapshot(old)
    new_before = _snapshot(new)
    out = tmp_path / "font-size.hwpx"
    old.compare(new, author="Format QA", date="2026-10-09T00:00:00Z", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    assert _snapshot(old) == old_before
    assert _snapshot(new) == new_before


def test_hwpx_paragraph_format_change_is_supported_without_mutating_inputs(tmp_path: Path):
    old, new = _one_para("Centered")
    new.paragraphs[0].alignment = "CENTER"
    plan = build_revision_plan(old, new, everywhere=False)
    assert len(plan.paragraph_formats) == 1
    _assert_paragraph_format_supported(old, new, tmp_path)


def test_hwpx_text_plus_char_format_change_is_supported(tmp_path: Path):
    old, new = _one_para("Alpha old tail")
    new.paragraphs[0].text = "Alpha new tail"
    new.paragraphs[0].runs[0].italic = True
    plan = build_revision_plan(old, new, everywhere=False)
    assert plan.paragraphs and plan.run_formats
    out = tmp_path / "text-plus-format.hwpx"
    old.compare(new, author="Format QA", date="2026-10-09T00:00:00Z", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok


def test_hwpx_named_style_reference_change_remains_fail_closed():
    old, new = _one_para("same")
    styles = list(new.styles)
    assert len(styles) > 1
    new.paragraphs[0].style_id_ref = styles[1].style_id
    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new, everywhere=False)
    assert excinfo.value.code == "compare-hwpx-style-reference-track-unsupported"


def test_hwpx_text_only_tracking_still_works(tmp_path: Path):
    old, new = _one_para("Alpha old tail")
    new.paragraphs[0].text = "Alpha new tail"
    review = tmp_path / "text-only-review.hwpx"
    old.compare(new, author="QA", date="2026-10-09T00:00:00Z", everywhere=False).save(review)
    assert validate_hwpx_file(review).ok
    reopened = Document.open(review)
    assert "Alpha" in reopened.paragraphs[0].text
