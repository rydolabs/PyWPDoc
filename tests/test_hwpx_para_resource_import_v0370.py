"""v0.37.0 resource-aware HWPX ParaShape import/remap.

The review document is a clone of NEW.  When OLD's paragraph property is not
present in NEW, the writer imports/remaps its tab/border/list dependency graph
instead of leaving an unresolved local id or failing for ordinary resources.
"""
from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest
from lxml import etree

from pywpdoc import Document, DocumentUnsupportedError
from pywpdoc.features.compare import build_revision_plan
from pywpdoc._engine import validate_hwpx_file
from pywpdoc._engine.model import ElementModel, local_name
from pywpdoc._engine.validation import validate_document_model

HH = "http://www.hancom.co.kr/hwpml/2011/head"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS = {"hh": HH, "hp": HP}


def _roots(path: Path):
    with ZipFile(path) as zf:
        return etree.fromstring(zf.read("Contents/header.xml")), etree.fromstring(zf.read("Contents/section0.xml"))


def _pair(text="Cross-document ParaShape"):
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    old.add_paragraph(text)
    new.add_paragraph(text)
    return old, new


def _native(doc: Document):
    return doc.backend.native


def _container(doc: Document, name: str):
    return next(n for n in _native(doc).header_model.iter() if local_name(n.tag) == name)


def _para_pr(doc: Document, paragraph_index: int = 0):
    paragraph = doc.paragraphs[paragraph_index]
    return _native(doc).styles.paragraph_property(paragraph.native.para_pr_id_ref)


def test_cross_document_old_parapr_is_imported_and_remapped(tmp_path: Path):
    old, new = _pair()
    old.paragraphs[0].paragraph_format.line_spacing_percent = 177
    new.paragraphs[0].paragraph_format.line_spacing_percent = 190
    before = new.backend.native.styles.paragraph_count

    out = tmp_path / "para-crossdoc.hwpx"
    old.compare(new, author="QA", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    assert new.backend.native.styles.paragraph_count == before  # NEW is not mutated

    header, section = _roots(out)
    change = header.xpath('.//hh:trackChange[@type="ParaShape"]', namespaces=NS)[0]
    para = section.xpath('.//hp:p[.//hp:t="Cross-document ParaShape"]', namespaces=NS)[0]
    assert para.get("paraTcId") == change.get("id")
    old_pp = header.xpath(f'.//hh:paraPr[@id="{change.get("parashapeID")}"]', namespaces=NS)[0]
    new_pp = header.xpath(f'.//hh:paraPr[@id="{para.get("paraPrIDRef")}"]', namespaces=NS)[0]
    assert old_pp.xpath('./hh:lineSpacing/@value', namespaces=NS) == ["177"]
    assert new_pp.xpath('./hh:lineSpacing/@value', namespaces=NS) == ["190"]


def test_parashape_semantic_compare_resolves_same_numeric_tab_ids(tmp_path: Path):
    old, new = _pair("Tab semantic collision")
    # Raw paraPr is unchanged and still points at tabPr 0 in both documents.
    # Only the OLD tabPr 0 definition changes. The planner must see that as a
    # paragraph-format change rather than treating equal numeric ids as equal.
    old_tab0 = next(c for c in _container(old, "tabProperties").children if local_name(c.tag) == "tabPr" and c.get("id") == "0")
    old_tab0.set("autoTabLeft", "1")
    assert _para_pr(old).get("tabPrIDRef") == _para_pr(new).get("tabPrIDRef") == "0"
    plan = build_revision_plan(old, new, everywhere=False)
    assert len(plan.paragraph_formats) == 1

    out = tmp_path / "tab-collision.hwpx"
    old.compare(new, author="QA", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    header, _ = _roots(out)
    change = header.xpath('.//hh:trackChange[@type="ParaShape"]', namespaces=NS)[0]
    old_pp = header.xpath(f'.//hh:paraPr[@id="{change.get("parashapeID")}"]', namespaces=NS)[0]
    # OLD tabPr 0 is semantically identical to NEW's existing tabPr 1, so it
    # should dedupe/remap rather than copy a second definition.
    assert old_pp.get("tabPrIDRef") == "1"


def test_parashape_borderfill_resource_collision_is_remapped(tmp_path: Path):
    old, new = _pair("Border semantic collision")
    # paraPr raw XML still points to borderFill 2 in both docs; only the OLD
    # definition behind id 2 differs.
    old_bf2 = next(c for c in _container(old, "borderFills").children if local_name(c.tag) == "borderFill" and c.get("id") == "2")
    old_bf2.set("shadow", "1" if old_bf2.get("shadow") != "1" else "0")
    plan = build_revision_plan(old, new, everywhere=False)
    assert len(plan.paragraph_formats) == 1

    out = tmp_path / "border-collision.hwpx"
    old.compare(new, author="QA", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    header, _ = _roots(out)
    change = header.xpath('.//hh:trackChange[@type="ParaShape"]', namespaces=NS)[0]
    old_pp = header.xpath(f'.//hh:paraPr[@id="{change.get("parashapeID")}"]', namespaces=NS)[0]
    border_ref = old_pp.xpath('./hh:border/@borderFillIDRef', namespaces=NS)[0]
    assert border_ref != "2"
    imported = header.xpath(f'.//hh:borderFill[@id="{border_ref}"]', namespaces=NS)[0]
    assert imported.get("shadow") == old_bf2.get("shadow")


def test_parashape_numbering_same_id_different_definition_imports_old_numbering(tmp_path: Path):
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    old.hwpx.add_list_paragraph("Numbering collision", kind="number", restart=True, start=3)
    new.hwpx.add_list_paragraph("Numbering collision", kind="number", restart=True, start=7)
    # Both independent documents allocate the newly authored numbering as id 2
    # and their paraPr heading idRef therefore collides numerically.
    old_heading = next(c for c in _para_pr(old).children if local_name(c.tag) == "heading")
    new_heading = next(c for c in _para_pr(new).children if local_name(c.tag) == "heading")
    assert old_heading.get("idRef") == new_heading.get("idRef") == "2"
    plan = build_revision_plan(old, new, everywhere=False)
    assert len(plan.paragraph_formats) == 1

    out = tmp_path / "numbering-remap.hwpx"
    old.compare(new, author="QA", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    header, section = _roots(out)
    change = header.xpath('.//hh:trackChange[@type="ParaShape"]', namespaces=NS)[0]
    para = section.xpath('.//hp:p[.//hp:t="Numbering collision"]', namespaces=NS)[0]
    old_pp = header.xpath(f'.//hh:paraPr[@id="{change.get("parashapeID")}"]', namespaces=NS)[0]
    current_pp = header.xpath(f'.//hh:paraPr[@id="{para.get("paraPrIDRef")}"]', namespaces=NS)[0]
    old_num_id = old_pp.xpath('./hh:heading/@idRef', namespaces=NS)[0]
    new_num_id = current_pp.xpath('./hh:heading/@idRef', namespaces=NS)[0]
    assert old_num_id != new_num_id
    assert header.xpath(f'.//hh:numbering[@id="{old_num_id}"]/@start', namespaces=NS) == ["3"]
    assert header.xpath(f'.//hh:numbering[@id="{new_num_id}"]/@start', namespaces=NS) == ["7"]


def test_parashape_bullet_same_id_different_definition_imports_old_bullet(tmp_path: Path):
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    old.hwpx.add_list_paragraph("Bullet collision", kind="bullet", levels=[{"char": "◈"}])
    new.hwpx.add_list_paragraph("Bullet collision", kind="bullet", levels=[{"char": "•"}])
    old_heading = next(c for c in _para_pr(old).children if local_name(c.tag) == "heading")
    new_heading = next(c for c in _para_pr(new).children if local_name(c.tag) == "heading")
    assert old_heading.get("idRef") == new_heading.get("idRef") == "1"
    plan = build_revision_plan(old, new, everywhere=False)
    assert len(plan.paragraph_formats) == 1

    out = tmp_path / "bullet-remap.hwpx"
    old.compare(new, author="QA", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    header, section = _roots(out)
    change = header.xpath('.//hh:trackChange[@type="ParaShape"]', namespaces=NS)[0]
    para = section.xpath('.//hp:p[.//hp:t="Bullet collision"]', namespaces=NS)[0]
    old_pp = header.xpath(f'.//hh:paraPr[@id="{change.get("parashapeID")}"]', namespaces=NS)[0]
    new_pp = header.xpath(f'.//hh:paraPr[@id="{para.get("paraPrIDRef")}"]', namespaces=NS)[0]
    old_bid = old_pp.xpath('./hh:heading/@idRef', namespaces=NS)[0]
    new_bid = new_pp.xpath('./hh:heading/@idRef', namespaces=NS)[0]
    assert old_bid != new_bid
    assert header.xpath(f'.//hh:bullet[@id="{old_bid}"]/@char', namespaces=NS) == ["◈"]
    assert header.xpath(f'.//hh:bullet[@id="{new_bid}"]/@char', namespaces=NS) == ["•"]


def test_parashape_numbering_parahead_charpr_dependency_is_remapped(tmp_path: Path):
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    old.hwpx.add_list_paragraph("Number char format", kind="number", restart=True, start=2)
    new.hwpx.add_list_paragraph("Number char format", kind="number", restart=True, start=8)

    # Give OLD numbering's paraHead a real OLD-only charPr rather than Hancom's
    # 4294967295 sentinel. The numbering importer must use the CharShape import
    # graph to remap that nested dependency too.
    marker = old.add_paragraph().add_run("marker")
    marker.font.name = "Old Number Marker Font"
    marker.font.size = 13
    old_char_id = marker.native.char_pr_id_ref
    numbering = next(c for c in _container(old, "numberings").children if local_name(c.tag) == "numbering" and c.get("id") == "2")
    for head in numbering.children:
        if local_name(head.tag) == "paraHead":
            head.set("charPrIDRef", str(old_char_id))
    # Keep paragraph structure aligned by adding an equivalent marker paragraph
    # to NEW, but with a different character format.
    new_marker = new.add_paragraph().add_run("marker")
    new_marker.font.name = "New Number Marker Font"
    new_marker.font.size = 11

    out = tmp_path / "numbering-charpr-remap.hwpx"
    old.compare(new, author="QA", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    header, _ = _roots(out)
    changes = header.xpath('.//hh:trackChange[@type="ParaShape"]', namespaces=NS)
    assert changes
    old_pp = header.xpath(f'.//hh:paraPr[@id="{changes[0].get("parashapeID")}"]', namespaces=NS)[0]
    old_num_id = old_pp.xpath('./hh:heading/@idRef', namespaces=NS)[0]
    refs = header.xpath(f'.//hh:numbering[@id="{old_num_id}"]/hh:paraHead/@charPrIDRef', namespaces=NS)
    assert refs and all(ref not in {"4294967295", "-1"} for ref in refs)
    for ref in refs:
        assert header.xpath(f'.//hh:charPr[@id="{ref}"]', namespaces=NS)


def test_malformed_image_bullet_without_binary_reference_stays_fail_closed_from_v0380():
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    old.hwpx.add_list_paragraph("Image bullet", kind="bullet", levels=[{"char": "◈"}])
    new.hwpx.add_list_paragraph("Image bullet", kind="bullet", levels=[{"char": "•"}])
    bullet = next(c for c in _container(old, "bullets").children if local_name(c.tag) == "bullet")
    bullet.set("useImage", "1")
    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new, author="QA", everywhere=False)
    assert excinfo.value.code == "compare-hwpx-format-resource-remap-failed"


def test_validator_rejects_dangling_parapr_and_parahead_resources():
    doc = Document.new("hwpx")
    doc.add_paragraph("Broken para refs")
    pp = _para_pr(doc)
    pp.set("tabPrIDRef", "999")
    border = next(c for c in pp.children if local_name(c.tag) == "border")
    border.set("borderFillIDRef", "999")

    # Add a numbering definition with a dangling charPr, then point the paraPr
    # to that numbering so both validator paths are exercised.
    nums = _container(doc, "numberings")
    source = next(c for c in nums.children if local_name(c.tag) == "numbering")
    num = ElementModel.from_dict(source.to_dict())
    num.set("id", "2")
    for head in num.children:
        if local_name(head.tag) == "paraHead":
            head.set("charPrIDRef", "999")
    nums.children.append(num)
    nums.set("itemCnt", "2")
    heading = next(c for c in pp.children if local_name(c.tag) == "heading")
    heading.set("type", "NUMBER")
    heading.set("idRef", "999")

    report = validate_document_model(_native(doc))
    codes = {issue.code for issue in report.issues}
    assert "tabpr-ref-missing" in codes
    assert "parapr-borderfill-ref-missing" in codes
    assert "parapr-numbering-ref-missing" in codes
    assert "parahead-charpr-ref-missing" in codes
