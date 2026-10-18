"""v0.36.0 HWPX ParaShape Track Changes candidate.

Evidence basis:
- Hancom OWPML model CPType serializes hp:p@paraTcId.
- Hancom OWPML trackChange serializes type=ParaShape with parashapeID.

The GUI gate in Hancom 2020 is intentionally external; these tests lock the
package/XML contract and safety boundaries before that gate is claimed passed.
"""
from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest
from lxml import etree

from pywpdoc import Document, DocumentUnsupportedError
from pywpdoc.features.compare import build_revision_plan
from pywpdoc._engine import validate_hwpx_file

HH = "http://www.hancom.co.kr/hwpml/2011/head"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS = {"hh": HH, "hp": HP}


def _roots(path: Path):
    with ZipFile(path) as zf:
        return (
            etree.fromstring(zf.read("Contents/header.xml")),
            etree.fromstring(zf.read("Contents/section0.xml")),
        )


def _pair(text: str = "Paragraph formatting: Alpha Beta") -> tuple[Document, Document]:
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    old.add_paragraph(text)
    new.add_paragraph(text)
    return old, new


def _para_pr(header, para_id: str):
    nodes = header.xpath(f'.//hh:paraPr[@id="{para_id}"]', namespaces=NS)
    assert len(nodes) == 1
    return nodes[0]


def test_hwpx_parashape_alignment_uses_paragraph_paratcid_and_old_shape(tmp_path: Path):
    old, new = _pair()
    new.paragraphs[0].alignment = "CENTER"
    plan = build_revision_plan(old, new, everywhere=False)
    assert plan.paragraphs == ()
    assert plan.run_formats == ()
    assert len(plan.paragraph_formats) == 1

    out = tmp_path / "para-format-review.hwpx"
    old.compare(new, author="Para QA", date="2026-10-12T13:00:00Z", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok

    header, section = _roots(out)
    changes = header.xpath('.//hh:trackChange[@type="ParaShape"]', namespaces=NS)
    assert len(changes) == 1
    change = changes[0]
    assert change.get("parashapeID") == "0"
    assert change.get("paraShapeID") is None

    paras = section.xpath('.//hp:p[.//hp:t="Paragraph formatting: Alpha Beta"]', namespaces=NS)
    assert len(paras) == 1
    para = paras[0]
    assert para.get("paraTcId") == change.get("id")
    assert para.get("paraPrIDRef") != change.get("parashapeID")

    current = _para_pr(header, para.get("paraPrIDRef"))
    old_shape = _para_pr(header, change.get("parashapeID"))
    assert current.xpath('./hh:align/@horizontal', namespaces=NS) == ["CENTER"]
    assert old_shape.xpath('./hh:align/@horizontal', namespaces=NS) == ["JUSTIFY"]

    assert not section.xpath('.//hp:insertBegin | .//hp:insertEnd | .//hp:deleteBegin | .//hp:deleteEnd', namespaces=NS)


def test_hwpx_parashape_line_spacing_tracks_old_and_new_parapr(tmp_path: Path):
    old, new = _pair("Line spacing: Alpha Beta")
    new.paragraphs[0].paragraph_format.line_spacing_percent = 190

    out = tmp_path / "line-spacing-review.hwpx"
    old.compare(new, author="Para QA", date="2026-10-12T13:05:00Z", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok

    header, section = _roots(out)
    change = header.xpath('.//hh:trackChange[@type="ParaShape"]', namespaces=NS)[0]
    para = section.xpath('.//hp:p[.//hp:t="Line spacing: Alpha Beta"]', namespaces=NS)[0]
    assert para.get("paraTcId") == change.get("id")
    current = _para_pr(header, para.get("paraPrIDRef"))
    old_shape = _para_pr(header, change.get("parashapeID"))
    assert current.xpath('./hh:lineSpacing/@value', namespaces=NS) == ["190"]
    assert old_shape.xpath('./hh:lineSpacing/@value', namespaces=NS) == ["160"]


def test_hwpx_parashape_can_coexist_with_text_and_char_tracking(tmp_path: Path):
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    old.add_paragraph("Alpha old tail")
    np = new.add_paragraph("Alpha new tail")
    np.alignment = "CENTER"
    np.runs[0].bold = True

    plan = build_revision_plan(old, new, everywhere=False)
    assert plan.paragraphs
    assert plan.run_formats
    assert plan.paragraph_formats

    out = tmp_path / "mixed-review.hwpx"
    old.compare(new, author="Para QA", date="2026-10-12T13:10:00Z", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    header, section = _roots(out)
    assert header.xpath('.//hh:trackChange[@type="ParaShape"]', namespaces=NS)
    assert header.xpath('.//hh:trackChange[@type="CharShape"]', namespaces=NS)
    assert header.xpath('.//hh:trackChange[@type="Insert"]', namespaces=NS)
    assert header.xpath('.//hh:trackChange[@type="Delete"]', namespaces=NS)
    assert section.xpath('.//hp:p[@paraTcId]', namespaces=NS)
    assert section.xpath('.//hp:run[@paraTcId]', namespaces=NS)


def test_hwpx_named_style_identity_change_still_fails_closed():
    old, new = _pair("Named style")
    styles = list(new.styles)
    assert len(styles) > 1
    new.paragraphs[0].style_id_ref = styles[1].style_id
    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new, everywhere=False)
    assert excinfo.value.code == "compare-hwpx-style-reference-track-unsupported"


def test_hwpx_existing_paragraph_paratcid_is_not_overlapped():
    old, new = _pair()
    new.paragraphs[0].alignment = "CENTER"
    new.paragraphs[0].native.element_model.set("paraTcId", "99")
    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new, everywhere=False)
    assert excinfo.value.code == "compare-existing-revisions-unsupported"


def test_hwpx_cross_document_missing_old_parapr_is_imported_from_v0370(tmp_path: Path):
    # v0.36 originally failed closed here. v0.37 imports/remaps ordinary OLD
    # ParaShape resources into the review clone, so preserve this historical
    # scenario as a positive regression instead.
    old, new = _pair("Cross document para")
    old.paragraphs[0].paragraph_format.line_spacing_percent = 177
    new.paragraphs[0].paragraph_format.line_spacing_percent = 190
    out = tmp_path / "cross-doc-para-v0370.hwpx"
    old.compare(new, everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    header, section = _roots(out)
    change = header.xpath('.//hh:trackChange[@type="ParaShape"]', namespaces=NS)[0]
    old_shape = _para_pr(header, change.get("parashapeID"))
    assert old_shape.xpath('./hh:lineSpacing/@value', namespaces=NS) == ["177"]
    para = section.xpath('.//hp:p[.//hp:t="Cross document para"]', namespaces=NS)[0]
    assert para.get("paraTcId") == change.get("id")
