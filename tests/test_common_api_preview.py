"""Experimental common facade tests; these become the seed for the standalone API."""
from __future__ import annotations

from pathlib import Path

import pytest

from pywpdoc._engine.common_api import UnifiedDocument


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_common_preview_create_save_open_mixed_text(kind: str, tmp_path: Path):
    doc = UnifiedDocument.new(kind)
    p = doc.add_paragraph()
    p.add_run("A\tB\nC")
    out = tmp_path / f"common.{kind}"
    doc.save(out)
    reopened = UnifiedDocument.open(out)
    assert reopened.format == kind
    assert reopened.paragraphs[-1].text == "A\tB\nC"


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_common_preview_replace_across_runs(kind: str, tmp_path: Path):
    doc = UnifiedDocument.new(kind)
    p = doc.add_paragraph()
    a = p.add_run("202")
    a.bold = True
    b = p.add_run("6학년도")
    b.italic = True
    assert doc.replace("2026", "2027") == 1
    assert p.text == "2027학년도"
    assert a.bold is True
    assert b.italic is True
    out = tmp_path / f"replace.{kind}"
    doc.save(out)
    assert UnifiedDocument.open(out).paragraphs[-1].text == "2027학년도"


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_common_preview_top_level_table_and_nested_table(kind: str, tmp_path: Path):
    doc = UnifiedDocument.new(kind)
    table = doc.add_table(1, 1, style="Table Grid")
    table.cell(0, 0).text = "outer"
    table.cell(0, 0).add_table(1, 1, style="Table Grid").cell(0, 0).text = "inner"
    assert len(doc.tables) == 1
    out = tmp_path / f"tables.{kind}"
    doc.save(out)
    assert len(UnifiedDocument.open(out).tables) == 1


def test_common_preview_expert_namespaces_are_explicit():
    from pywpdoc._engine import HwpxUnsupportedError

    hwpx = UnifiedDocument.new("hwpx")
    assert hwpx.hwpx is hwpx.native
    with pytest.raises(HwpxUnsupportedError):
        _ = hwpx.docx

    docx = UnifiedDocument.new("docx")
    assert docx.docx is docx.native
    with pytest.raises(HwpxUnsupportedError):
        _ = docx.hwpx


def test_common_preview_unknown_extension_fails_closed(tmp_path: Path):
    from pywpdoc._engine import HwpxValueError

    path = tmp_path / "x.bin"
    path.write_bytes(b"x")
    with pytest.raises(HwpxValueError) as exc:
        UnifiedDocument.open(path)
    assert exc.value.code == "common-format-unknown"
