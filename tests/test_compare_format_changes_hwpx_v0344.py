"""v0.34.4 Hancom 2020-native HWPX character-format Track Changes.

Native oracle: a Hancom 2020-authored formatting revision created from the
project's formatting-only QA document.  The editor emits:
- hh:trackChange type="CharShape" with charshapeID=<old charPr id>
- the changed hp:run carries paraTcId=<trackChange id>
- hh:trackchageConfig flags has bit 0 enabled (56 -> 57 in the fixture)

Paragraph-format (ParaShape) authoring is activated in v0.36.0 from Hancom's public OWPML model contract; v0.34.4 itself only covered CharShape.
"""
from __future__ import annotations

from pathlib import Path
import json
from zipfile import ZipFile

import pytest
from lxml import etree

from pywpdoc import Document, DocumentUnsupportedError
from pywpdoc.features.compare import build_revision_plan
from pywpdoc._engine import validate_hwpx_file

HH = "http://www.hancom.co.kr/hwpml/2011/head"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS = {"hh": HH, "hp": HP}
CONTRACT = json.loads((Path(__file__).parent / "fixtures" / "hancom2020_charshape_track_contract.json").read_text())


def _format_pair() -> tuple[Document, Document]:
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    op = old.add_paragraph()
    op.add_run("Font + bold + size: ")
    op.add_run("Alpha Beta")
    np = new.add_paragraph()
    np.add_run("Font + bold + size: ")
    target = np.add_run("Alpha Beta")
    target.bold = True
    target.font.size = 16
    return old, new


def _roots(path: Path):
    with ZipFile(path) as zf:
        return (
            etree.fromstring(zf.read("Contents/header.xml")),
            etree.fromstring(zf.read("Contents/section0.xml")),
        )


def test_hwpx_char_format_uses_hancom2020_native_anchor_and_old_shape(tmp_path: Path):
    old, new = _format_pair()
    plan = build_revision_plan(old, new, everywhere=False)
    assert plan.paragraphs == ()
    assert plan.paragraph_formats == ()
    assert len(plan.run_formats) == 1

    out = tmp_path / "char-format-review.hwpx"
    old.compare(new, author="user", date="2026-10-12T11:26:00Z", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok

    header, section = _roots(out)
    changes = header.xpath('.//hh:trackChange[@type="CharShape"]', namespaces=NS)
    assert len(changes) == 1
    change = changes[0]
    change_id = change.get("id")
    assert change_id
    # Native Hancom 2020 output uses lower-case "shape" here.
    assert change.get(CONTRACT["native_old_shape_attribute"]) == CONTRACT["old_charpr"]["id"]
    assert change.get("charShapeID") is None
    assert change.get("authorID") == CONTRACT["track_change"]["authorID"]
    assert change.get("hide") == CONTRACT["track_change"]["hide"]

    configs = header.xpath('.//hh:trackchageConfig', namespaces=NS)
    assert len(configs) == 1
    assert int(configs[0].get("flags")) & 1 == 1

    runs = section.xpath('.//hp:run[hp:t="Alpha Beta"]', namespaces=NS)
    assert len(runs) == 1
    target = runs[0]
    # This is the key Hancom 2020 native quirk established by the supplied file.
    assert target.get(CONTRACT["native_anchor_attribute"]) == change_id
    assert target.get(CONTRACT["schema_anchor_attribute_not_used_by_hancom2020"]) is None
    assert target.get("charPrIDRef") != CONTRACT["old_charpr"]["id"]
    current = header.xpath(f'.//hh:charPr[@id="{target.get("charPrIDRef")}"]', namespaces=NS)[0]
    assert current.get("height") == CONTRACT["new_charpr"]["height"]
    assert bool(current.xpath('./hh:bold', namespaces=NS)) is CONTRACT["new_charpr"]["bold"]

    prefix = section.xpath('.//hp:run[hp:t="Font + bold + size: "]', namespaces=NS)
    assert len(prefix) == 1
    assert prefix[0].get("paraTcId") is None

    # Pure format revision: no insert/delete range markers.
    assert not section.xpath('.//hp:insertBegin | .//hp:insertEnd | .//hp:deleteBegin | .//hp:deleteEnd', namespaces=NS)


def test_hwpx_char_format_reject_projection_restores_old_charpr(tmp_path: Path):
    old, new = _format_pair()
    out = tmp_path / "review.hwpx"
    old.compare(new, author="user", date="2026-10-12T11:26:00Z", everywhere=False).save(out)
    header, section = _roots(out)
    change = header.xpath('.//hh:trackChange[@type="CharShape"]', namespaces=NS)[0]
    run = section.xpath('.//hp:run[hp:t="Alpha Beta"]', namespaces=NS)[0]
    assert run.get("charPrIDRef") != change.get("charshapeID")
    # Native semantic contract: accept keeps current charPr; reject restores the old id.
    accepted_charpr = run.get("charPrIDRef")
    rejected_charpr = change.get("charshapeID")
    assert accepted_charpr != "0"
    assert rejected_charpr == "0"


def test_hwpx_char_format_can_coexist_with_text_tracking(tmp_path: Path):
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    old.add_paragraph("Alpha old tail")
    np = new.add_paragraph("Alpha new tail")
    np.runs[0].bold = True

    plan = build_revision_plan(old, new, everywhere=False)
    assert plan.paragraphs
    assert plan.run_formats

    out = tmp_path / "mixed.hwpx"
    old.compare(new, author="QA", date="2026-10-12T11:26:00Z", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    header, section = _roots(out)
    assert header.xpath('.//hh:trackChange[@type="CharShape"]', namespaces=NS)
    assert header.xpath('.//hh:trackChange[@type="Insert"]', namespaces=NS)
    assert header.xpath('.//hh:trackChange[@type="Delete"]', namespaces=NS)
    assert section.xpath('.//hp:run[@paraTcId]', namespaces=NS)
    assert section.xpath('.//hp:insertBegin | .//hp:deleteBegin', namespaces=NS)


def test_hwpx_paragraph_format_is_supported_by_v0360_model_contract(tmp_path: Path):
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    old.add_paragraph("Centered")
    new.add_paragraph("Centered")
    new.paragraphs[0].alignment = "CENTER"

    plan = build_revision_plan(old, new, everywhere=False)
    assert plan.paragraph_formats
    out = tmp_path / "para-format.hwpx"
    old.compare(new, everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    header, section = _roots(out)
    change = header.xpath('.//hh:trackChange[@type="ParaShape"]', namespaces=NS)[0]
    para = section.xpath('.//hp:p[.//hp:t="Centered"]', namespaces=NS)[0]
    assert para.get("paraTcId") == change.get("id")
    assert change.get("parashapeID") == "0"


def test_hwpx_existing_native_run_paratcid_is_not_overlapped():
    old, new = _format_pair()
    new.paragraphs[0].runs[-1].element_model.set("paraTcId", "99")
    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new, everywhere=False)
    assert excinfo.value.code == "compare-existing-revisions-unsupported"
