"""v0.39.0 semantic named-style identity gating for HWPX comparison.

HWPX style ids are header-local.  CharShape/ParaShape Track Changes can restore
format properties, but there is no verified track-change record for changing a
paragraph's named-style identity itself.  These tests make that boundary
semantic rather than numeric.
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


def _pair(text="Semantic style identity"):
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    old.add_paragraph(text)
    new.add_paragraph(text)
    return old, new


def _equivalent_style_with_new_local_id(doc: Document, source_name="Body"):
    source = doc.styles[source_name]
    created = doc.styles.add_style("Temporary Equivalent Style", clone_from=source_name)
    # Copy all non-reference identity metadata. Keep property refs local to this
    # document and make next-style self-referential under the new local id.
    for attr in ("type", "name", "engName", "langID", "lockForm"):
        value = source.element_model.get(attr)
        if value is not None:
            created.element_model.set(attr, value)
    created.para_pr_id_ref = source.para_pr_id_ref or "0"
    created.char_pr_id_ref = source.char_pr_id_ref or "0"
    created.next_style_id_ref = created.id
    return source, created


def test_equivalent_named_style_different_local_id_is_not_a_format_change():
    old, new = _pair()
    old_body = old.styles["Body"]
    _, new_body_alias = _equivalent_style_with_new_local_id(new, "Body")
    old.paragraphs[0].style_id_ref = old_body.id
    new.paragraphs[0].style_id_ref = new_body_alias.id
    old.paragraphs[0].native.para_pr_id_ref = old_body.para_pr_id_ref or "0"
    new.paragraphs[0].native.para_pr_id_ref = new_body_alias.para_pr_id_ref or "0"

    plan = build_revision_plan(old, new, everywhere=False)
    assert plan.change_count == 0
    assert plan.paragraph_formats == ()


def test_equivalent_named_style_different_local_id_allows_parashape_tracking(tmp_path: Path):
    old, new = _pair("Equivalent style plus spacing")
    old_body = old.styles["Body"]
    _, new_body_alias = _equivalent_style_with_new_local_id(new, "Body")
    old.paragraphs[0].style_id_ref = old_body.id
    new.paragraphs[0].style_id_ref = new_body_alias.id
    old.paragraphs[0].native.para_pr_id_ref = old_body.para_pr_id_ref or "0"
    new.paragraphs[0].native.para_pr_id_ref = new_body_alias.para_pr_id_ref or "0"
    old.paragraphs[0].paragraph_format.line_spacing_percent = 177
    new.paragraphs[0].paragraph_format.line_spacing_percent = 190

    plan = build_revision_plan(old, new, everywhere=False)
    assert len(plan.paragraph_formats) == 1

    out = tmp_path / "style-id-remap-review.hwpx"
    old.compare(new, author="Style QA", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    with ZipFile(out) as zf:
        header = etree.fromstring(zf.read("Contents/header.xml"))
        section = etree.fromstring(zf.read("Contents/section0.xml"))
    change = header.xpath('.//hh:trackChange[@type="ParaShape"]', namespaces=NS)[0]
    para = section.xpath('.//hp:p[.//hp:t="Equivalent style plus spacing"]', namespaces=NS)[0]
    # Review remains a clone of NEW: its named-style id stays NEW-local while
    # ParaShape change metadata points at the imported/remapped OLD paraPr.
    assert para.get("styleIDRef") == new_body_alias.id
    assert para.get("paraTcId") == change.get("id")
    old_pp = header.xpath(f'.//hh:paraPr[@id="{change.get("parashapeID")}"]', namespaces=NS)[0]
    current_pp = header.xpath(f'.//hh:paraPr[@id="{para.get("paraPrIDRef")}"]', namespaces=NS)[0]
    assert old_pp.xpath('./hh:lineSpacing/@value', namespaces=NS) == ["177"]
    assert current_pp.xpath('./hh:lineSpacing/@value', namespaces=NS) == ["190"]


def test_same_numeric_style_id_with_different_identity_fails_closed():
    old, new = _pair("Same id, different style")
    assert old.paragraphs[0].style_id_ref == new.paragraphs[0].style_id_ref == "0"
    # Mutate the definition behind the same local id. v0.38.0 compared only the
    # numeric styleIDRef and could silently miss this identity change.
    new_normal = new.styles[0]
    new_normal.name = "Different Normal Identity"
    new_normal.eng_name = "Different Normal Identity"

    plan = build_revision_plan(old, new, everywhere=False)
    assert len(plan.paragraph_formats) == 1
    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new, everywhere=False)
    assert excinfo.value.code == "compare-hwpx-style-reference-track-unsupported"
    assert excinfo.value.context["old_style_id"] == "0"
    assert excinfo.value.context["new_style_id"] == "0"


def test_different_semantic_named_style_still_fails_closed():
    old, new = _pair("Named style remains unsupported")
    old.paragraphs[0].style_id_ref = old.styles["Normal"].id
    new.paragraphs[0].style_id_ref = new.styles["Body"].id
    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new, everywhere=False)
    assert excinfo.value.code == "compare-hwpx-style-reference-track-unsupported"


def test_next_style_ids_are_compared_by_target_identity_not_local_number():
    old, new = _pair("Next style identity")
    old_body = old.styles["Body"]
    _, new_body_alias = _equivalent_style_with_new_local_id(new, "Body")
    old.paragraphs[0].style_id_ref = old_body.id
    new.paragraphs[0].style_id_ref = new_body_alias.id
    old.paragraphs[0].native.para_pr_id_ref = old_body.para_pr_id_ref or "0"
    new.paragraphs[0].native.para_pr_id_ref = new_body_alias.para_pr_id_ref or "0"
    # Both styles' next style is themselves, but the numeric ids differ.
    assert old_body.next_style_id_ref != new_body_alias.next_style_id_ref
    plan = build_revision_plan(old, new, everywhere=False)
    assert plan.change_count == 0
