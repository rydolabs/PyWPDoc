"""v0.38.0 cross-document image-bullet ParaShape resource import/remap."""
from __future__ import annotations

from base64 import b64decode
from pathlib import Path
from zipfile import ZipFile

import pytest
from lxml import etree

from pywpdoc import Document, DocumentUnsupportedError
from pywpdoc.features.compare import build_revision_plan
from pywpdoc._engine import validate_hwpx_file
from pywpdoc._engine.authoring import add_binary_image
from pywpdoc._engine.model import ElementModel, HC, local_name
from pywpdoc._engine.validation import validate_document_model

HH = "http://www.hancom.co.kr/hwpml/2011/head"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
OPF = "http://www.idpf.org/2007/opf/"
NS = {"hh": HH, "hp": HP, "opf": OPF, "hc": "http://www.hancom.co.kr/hwpml/2011/core"}

PNG_A = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZQmcAAAAASUVORK5CYII=")
PNG_B = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


def _native(doc: Document):
    return doc.backend.native


def _container(doc: Document, name: str):
    return next(n for n in _native(doc).header_model.iter() if local_name(n.tag) == name)


def _first_bullet(doc: Document):
    return next(c for c in _container(doc, "bullets").children if local_name(c.tag) == "bullet")


def _set_image_bullet(doc: Document, payload: bytes, *, text: str = "Image bullet") -> str:
    paragraph = doc.hwpx.add_list_paragraph(text, kind="bullet", levels=[{"char": "□"}])
    item_id = add_binary_image(_native(doc), payload, "png")
    bullet = _first_bullet(doc)
    bullet.set("useImage", "1")
    bullet.children.insert(0, ElementModel(HC + "img", attrs=[
        ("binaryItemIDRef", item_id), ("bright", "0"), ("contrast", "0"), ("effect", "REAL_PIC"), ("alpha", "0"),
    ]))
    return paragraph.text


def _roots(path: Path):
    with ZipFile(path) as zf:
        return (
            etree.fromstring(zf.read("Contents/header.xml")),
            etree.fromstring(zf.read("Contents/section0.xml")),
            etree.fromstring(zf.read("Contents/content.hpf")),
        )


def _paragraph_resource_ids(header, section, text: str):
    para = section.xpath(f'.//hp:p[.//hp:t="{text}"]', namespaces=NS)[0]
    changes = header.xpath('.//hh:trackChange[@type="ParaShape"]', namespaces=NS)
    change = next(c for c in changes if c.get("id") == para.get("paraTcId"))
    old_pp = header.xpath(f'.//hh:paraPr[@id="{change.get("parashapeID")}"]', namespaces=NS)[0]
    new_pp = header.xpath(f'.//hh:paraPr[@id="{para.get("paraPrIDRef")}"]', namespaces=NS)[0]
    return (
        old_pp.xpath('./hh:heading/@idRef', namespaces=NS)[0],
        new_pp.xpath('./hh:heading/@idRef', namespaces=NS)[0],
    )


def test_image_bullet_same_local_ids_different_payloads_are_detected_and_imported(tmp_path: Path):
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    _set_image_bullet(old, PNG_A)
    _set_image_bullet(new, PNG_B)
    # Both independently-created headers use bullet id=1 and manifest id=image1.
    assert _first_bullet(old).get("id") == _first_bullet(new).get("id") == "1"
    old_img = next(c for c in _first_bullet(old).children if local_name(c.tag) == "img")
    new_img = next(c for c in _first_bullet(new).children if local_name(c.tag) == "img")
    assert old_img.get("binaryItemIDRef") == new_img.get("binaryItemIDRef") == "image1"

    plan = build_revision_plan(old, new, everywhere=False)
    assert len(plan.paragraph_formats) == 1

    new_native = _native(new)
    before_parts = set(new_native._package.parts)
    before_manifest = [c.to_dict() for c in next(n for n in new_native.content_model.iter() if local_name(n.tag) == "manifest").children]

    out = tmp_path / "image-bullet-remap.hwpx"
    old.compare(new, author="QA", date="2026-10-12T14:00:00Z", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    assert set(new_native._package.parts) == before_parts
    assert [c.to_dict() for c in next(n for n in new_native.content_model.iter() if local_name(n.tag) == "manifest").children] == before_manifest

    header, section, hpf = _roots(out)
    old_bid, new_bid = _paragraph_resource_ids(header, section, "Image bullet")
    assert old_bid != new_bid
    old_ref = header.xpath(f'.//hh:bullet[@id="{old_bid}"]/*[local-name()="img"]/@binaryItemIDRef', namespaces=NS)[0]
    new_ref = header.xpath(f'.//hh:bullet[@id="{new_bid}"]/*[local-name()="img"]/@binaryItemIDRef', namespaces=NS)[0]
    assert old_ref != new_ref
    hrefs = {item.get("id"): item.get("href") for item in hpf.xpath('.//opf:manifest/opf:item', namespaces=NS)}
    assert old_ref in hrefs and new_ref in hrefs
    with ZipFile(out) as zf:
        assert zf.read(hrefs[old_ref]) == PNG_A
        assert zf.read(hrefs[new_ref]) == PNG_B


def test_image_bullet_import_deduplicates_existing_target_payload(tmp_path: Path):
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    _set_image_bullet(old, PNG_A)
    # Seed NEW with the OLD payload under image1, then give its current bullet a
    # different payload under image2. Import should reuse image1, not create image3.
    existing_old_id = add_binary_image(_native(new), PNG_A, "png")
    assert existing_old_id == "image1"
    _set_image_bullet(new, PNG_B)
    new_bullet = _first_bullet(new)
    new_img = next(c for c in new_bullet.children if local_name(c.tag) == "img")
    # _set_image_bullet adds the next available id because image1 is occupied.
    assert new_img.get("binaryItemIDRef") == "image2"

    out = tmp_path / "image-bullet-dedupe.hwpx"
    old.compare(new, author="QA", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    header, section, hpf = _roots(out)
    old_bid, _ = _paragraph_resource_ids(header, section, "Image bullet")
    old_ref = header.xpath(f'.//hh:bullet[@id="{old_bid}"]/*[local-name()="img"]/@binaryItemIDRef', namespaces=NS)[0]
    assert old_ref == "image1"
    image_items = hpf.xpath('.//opf:manifest/opf:item[starts-with(@id,"image")]/@id', namespaces=NS)
    assert image_items == ["image1", "image2"]
    with ZipFile(out) as zf:
        assert "BinData/image3.png" not in zf.namelist()


def test_image_bullet_missing_payload_fails_closed():
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    _set_image_bullet(old, PNG_A)
    _set_image_bullet(new, PNG_B)
    _native(old)._package.remove("BinData/image1.png")
    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new, author="QA", everywhere=False)
    assert excinfo.value.code == "compare-hwpx-format-source-resource-missing"


def test_validator_rejects_dangling_image_bullet_manifest_and_payload():
    doc = Document.new("hwpx")
    _set_image_bullet(doc, PNG_A)
    bullet = _first_bullet(doc)
    img = next(c for c in bullet.children if local_name(c.tag) == "img")
    img.set("binaryItemIDRef", "missing-image")
    report = validate_document_model(_native(doc))
    assert not report.ok
    assert any(issue.code == "bullet-image-manifest-ref-missing" for issue in report.errors)

    img.set("binaryItemIDRef", "image1")
    _native(doc)._package.remove("BinData/image1.png")
    report = validate_document_model(_native(doc))
    assert not report.ok
    assert any(issue.code == "bullet-image-payload-missing" for issue in report.errors)
