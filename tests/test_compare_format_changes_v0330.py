"""v0.33 tracked formatting revisions for DOCX; HWPX stays fail-closed."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile

import pytest
from lxml import etree
from docx import Document as NativeDocx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

from pywpdoc import Document, DocumentUnsupportedError
from pywpdoc.features.compare import build_revision_plan

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def _roundtrip_docx_projection(path: Path, tmp_path: Path, *, accepted: bool) -> NativeDocx:
    """Project only formatting revisions; test fixtures contain no text revisions."""
    native = NativeDocx(path)
    root = native.element

    for change in list(root.xpath(".//w:rPrChange")):
        parent = change.getparent()
        assert parent is not None and etree.QName(parent).localname == "rPr"
        if accepted:
            parent.remove(change)
            continue
        old = change.find(qn("w:rPr"))
        keep = [child for child in parent if child is not change]
        for child in keep:
            parent.remove(child)
        if old is not None:
            for child in list(old):
                parent.append(deepcopy(child))
        parent.remove(change)

    for change in list(root.xpath(".//w:pPrChange")):
        parent = change.getparent()
        assert parent is not None and etree.QName(parent).localname == "pPr"
        if accepted:
            parent.remove(change)
            continue
        old = change.find(qn("w:pPr"))
        # Section properties are not part of this v0.33 format-change target.
        sect = parent.find(qn("w:sectPr"))
        for child in list(parent):
            if child is change or child is sect:
                continue
            parent.remove(child)
        if old is not None:
            for child in list(old):
                parent.insert(0, deepcopy(child))
        parent.remove(change)

    out = tmp_path / ("accepted.docx" if accepted else "rejected.docx")
    native.save(out)
    return NativeDocx(out)


def _one_para_pair(text: str = "Alpha Beta"):
    old = Document.new("docx")
    new = Document.new("docx")
    old.add_paragraph(text)
    new.add_paragraph(text)
    return old, new


def test_docx_run_format_only_generates_rprchange_and_roundtrips(tmp_path: Path):
    old, new = _one_para_pair()
    old.paragraphs[0].runs[0].bold = False
    new.paragraphs[0].runs[0].bold = True
    new.paragraphs[0].runs[0].font.size = Pt(14)

    plan = build_revision_plan(old, new, everywhere=False)
    assert plan.paragraphs == ()
    assert len(plan.run_formats) == 1
    assert plan.change_count == 1

    out = tmp_path / "run-format.docx"
    old.compare(new, author="Format QA", date="2026-10-08T08:00:00Z", everywhere=False).save(out)

    with ZipFile(out) as zf:
        document = etree.fromstring(zf.read("word/document.xml"))
        settings = etree.fromstring(zf.read("word/settings.xml"))
    changes = document.xpath(".//w:rPrChange", namespaces=NS)
    assert len(changes) == 1
    assert changes[0].get(qn("w:author")) == "Format QA"
    assert changes[0].get(qn("w:date")) == "2026-10-08T08:00:00Z"
    assert document.xpath("count(.//w:ins | .//w:del)", namespaces=NS) == 0.0
    assert len(settings.xpath("./w:trackRevisions", namespaces=NS)) == 1

    accepted = _roundtrip_docx_projection(out, tmp_path, accepted=True)
    rejected = _roundtrip_docx_projection(out, tmp_path, accepted=False)
    assert accepted.paragraphs[0].runs[0].bold is True
    assert accepted.paragraphs[0].runs[0].font.size.pt == pytest.approx(14.0, abs=0.05)
    assert rejected.paragraphs[0].runs[0].bold is False


def test_docx_paragraph_format_only_generates_pprchange_and_roundtrips(tmp_path: Path):
    old, new = _one_para_pair("Centered")
    new.paragraphs[0].native.alignment = WD_ALIGN_PARAGRAPH.CENTER
    new.paragraphs[0].native.paragraph_format.space_before = Pt(12)

    plan = build_revision_plan(old, new, everywhere=False)
    assert len(plan.paragraph_formats) == 1
    assert plan.change_count == 1

    out = tmp_path / "paragraph-format.docx"
    old.compare(new, author="Format QA", date="2026-10-08T08:00:00Z", everywhere=False).save(out)
    with ZipFile(out) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
    changes = root.xpath(".//w:pPrChange", namespaces=NS)
    assert len(changes) == 1
    assert changes[0].xpath("./w:pPr", namespaces=NS)

    accepted = _roundtrip_docx_projection(out, tmp_path, accepted=True)
    rejected = _roundtrip_docx_projection(out, tmp_path, accepted=False)
    assert accepted.paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert accepted.paragraphs[0].paragraph_format.space_before.pt == pytest.approx(12.0, abs=0.05)
    assert rejected.paragraphs[0].alignment is None
    assert rejected.paragraphs[0].paragraph_format.space_before is None


def test_docx_run_boundary_differences_do_not_create_false_format_change():
    old = Document.new("docx")
    new = Document.new("docx")
    op = old.add_paragraph()
    op.add_run("Alpha ")
    op.add_run("Beta")
    new.add_paragraph("Alpha Beta")

    plan = build_revision_plan(old, new, everywhere=False)
    assert plan.change_count == 0
    assert plan.run_formats == ()


def test_docx_format_change_range_is_split_at_both_run_boundaries(tmp_path: Path):
    old = Document.new("docx")
    new = Document.new("docx")
    op = old.add_paragraph()
    op.add_run("Alpha ")
    op.add_run("Beta")
    np = new.add_paragraph("Alpha Beta")
    np.runs[0].bold = True

    plan = build_revision_plan(old, new, everywhere=False)
    assert [(r.new_start, r.new_end) for r in plan.run_formats] == [(0, 6), (6, 10)]

    out = tmp_path / "split.docx"
    old.compare(new, everywhere=False).save(out)
    with ZipFile(out) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
    assert len(root.xpath(".//w:rPrChange", namespaces=NS)) == 2
    assert "".join(root.xpath(".//w:t/text()", namespaces=NS)) == "Alpha Beta"


def test_docx_text_and_format_change_can_coexist_on_equal_text(tmp_path: Path):
    old = Document.new("docx")
    new = Document.new("docx")
    old.add_paragraph("Alpha old tail")
    np = new.add_paragraph("Alpha new tail")
    # Equal suffix changes formatting while the middle token changes text.
    np.runs[0].italic = True

    plan = build_revision_plan(old, new, everywhere=False)
    assert len(plan.paragraphs) == 1
    assert plan.run_formats

    out = tmp_path / "mixed.docx"
    old.compare(new, author="QA", date="2026-10-08T08:00:00Z", everywhere=False).save(out)
    with ZipFile(out) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
    assert root.xpath(".//w:ins", namespaces=NS)
    assert root.xpath(".//w:del", namespaces=NS)
    assert root.xpath(".//w:rPrChange", namespaces=NS)
    assert Document.open(out).format == "docx"


def test_hwpx_char_format_change_is_supported_after_native_hancom2020_oracle(tmp_path: Path):
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    old.add_paragraph("same")
    new.add_paragraph("same")
    old_before = old.paragraphs[0].runs[0].char_pr_id_ref
    new.paragraphs[0].runs[0].bold = True
    new_after = new.paragraphs[0].runs[0].char_pr_id_ref
    assert new_after != old_before

    out = tmp_path / "hwpx-char-format.hwpx"
    old.compare(new, everywhere=False).save(out)
    assert out.exists()
    assert old.paragraphs[0].runs[0].char_pr_id_ref == old_before
    assert new.paragraphs[0].runs[0].char_pr_id_ref == new_after


def test_docx_section_property_change_fails_closed():
    old, new = _one_para_pair("same")
    # The final section property lives at body level in python-docx; attach an
    # explicit paragraph section property to exercise the planner guard.
    ppr = new.paragraphs[0].native._p.get_or_add_pPr()
    ppr.append(deepcopy(new.native.sections[0]._sectPr))

    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new, everywhere=False)
    assert excinfo.value.code == "compare-section-format-change-unsupported"
