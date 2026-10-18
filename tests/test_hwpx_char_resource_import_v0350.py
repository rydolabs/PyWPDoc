"""v0.35.0 resource-aware HWPX CharShape import/remap."""
from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from pywpdoc import Document, DocumentUnsupportedError
from pywpdoc._engine import validate_hwpx_file
from pywpdoc._engine.validation import validate_document_model
from pywpdoc._engine.model import ElementModel, HH, local_name

HH_NS = "http://www.hancom.co.kr/hwpml/2011/head"
HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS = {"hh": HH_NS, "hp": HP_NS}
LANG_ATTRS = {"HANGUL":"hangul", "LATIN":"latin", "HANJA":"hanja", "JAPANESE":"japanese", "OTHER":"other", "SYMBOL":"symbol", "USER":"user"}


def _pair(old_font="PyWPDoc Legacy CrossDoc", new_font="PyWPDoc Modern CrossDoc"):
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    op = old.add_paragraph()
    op.add_run("Resource import: ")
    oru = op.add_run("Alpha Beta")
    oru.font.name = old_font
    oru.font.size = 10
    np = new.add_paragraph()
    np.add_run("Resource import: ")
    nru = np.add_run("Alpha Beta")
    nru.font.name = new_font
    nru.font.size = 16
    nru.bold = True
    return old, new


def _roots(path: Path):
    with ZipFile(path) as zf:
        return etree.fromstring(zf.read("Contents/header.xml")), etree.fromstring(zf.read("Contents/section0.xml"))


def _font_faces(header, charpr):
    ref = charpr.xpath('./hh:fontRef', namespaces=NS)[0]
    result = {}
    for lang, attr in LANG_ATTRS.items():
        fid = ref.get(attr)
        font = header.xpath(f'.//hh:fontface[@lang="{lang}"]/hh:font[@id="{fid}"]', namespaces=NS)
        assert len(font) == 1
        result[lang] = font[0].get("face")
    return result


def test_cross_document_old_charshape_resources_are_imported_and_remapped(tmp_path: Path):
    old, new = _pair()
    before_new_char_count = new.styles.char_count
    out = tmp_path / "cross-doc-review.hwpx"
    old.compare(new, author="QA", date="2026-10-12T12:00:00Z", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    # compare must not mutate the caller's NEW document.
    assert new.styles.char_count == before_new_char_count

    header, section = _roots(out)
    change = header.xpath('.//hh:trackChange[@type="CharShape"]', namespaces=NS)[0]
    old_id = change.get("charshapeID")
    assert old_id is not None
    old_charpr = header.xpath(f'.//hh:charPr[@id="{old_id}"]', namespaces=NS)[0]
    assert set(_font_faces(header, old_charpr).values()) == {"PyWPDoc Legacy CrossDoc"}
    assert old_charpr.get("height") == "1000"

    run = section.xpath('.//hp:run[hp:t="Alpha Beta"]', namespaces=NS)[0]
    assert run.get("paraTcId") == change.get("id")
    current = header.xpath(f'.//hh:charPr[@id="{run.get("charPrIDRef")}"]', namespaces=NS)[0]
    assert set(_font_faces(header, current).values()) == {"PyWPDoc Modern CrossDoc"}
    assert current.get("height") == "1600"
    assert current.xpath('./hh:bold', namespaces=NS)


def test_charshape_semantic_matching_resolves_font_ids_not_just_numbers(tmp_path: Path):
    old, new = _pair("Legacy Same Numeric IDs", "Different Same Numeric IDs")
    # Independent documents commonly allocate their custom font as the same numeric
    # id.  The old implementation could falsely treat charPr as equivalent solely
    # because the raw fontRef ids matched.
    old_cp = old.backend.native.styles.char_property(old.paragraphs[-1].runs[-1].element_model.get("charPrIDRef"))
    new_cp = new.backend.native.styles.char_property(new.paragraphs[-1].runs[-1].element_model.get("charPrIDRef"))
    old_ref = next(c for c in old_cp.children if local_name(c.tag) == "fontRef")
    new_ref = next(c for c in new_cp.children if local_name(c.tag) == "fontRef")
    assert old_ref.get("hangul") == new_ref.get("hangul")

    out = tmp_path / "semantic-font-review.hwpx"
    old.compare(new, author="QA", everywhere=False).save(out)
    header, _ = _roots(out)
    change = header.xpath('.//hh:trackChange[@type="CharShape"]', namespaces=NS)[0]
    old_charpr = header.xpath(f'.//hh:charPr[@id="{change.get("charshapeID")}"]', namespaces=NS)[0]
    assert set(_font_faces(header, old_charpr).values()) == {"Legacy Same Numeric IDs"}


def test_repeated_old_charshape_import_deduplicates_fonts_and_charpr(tmp_path: Path):
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    for text in ("Alpha", "Beta"):
        p = old.add_paragraph()
        r = p.add_run(text); r.font.name = "One Legacy Font"; r.font.size = 11
        p2 = new.add_paragraph()
        r2 = p2.add_run(text); r2.font.name = "One New Font"; r2.font.size = 15; r2.bold = True
    out = tmp_path / "dedup.hwpx"
    old.compare(new, author="QA", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    header, _ = _roots(out)
    changes = header.xpath('.//hh:trackChange[@type="CharShape"]', namespaces=NS)
    assert len(changes) == 2
    assert len({c.get("charshapeID") for c in changes}) == 1
    for lang in LANG_ATTRS:
        matches = header.xpath(f'.//hh:fontface[@lang="{lang}"]/hh:font[@face="One Legacy Font"]', namespaces=NS)
        assert len(matches) == 1


def test_charshape_borderfill_is_imported_and_remapped(tmp_path: Path):
    old, new = _pair()
    old_native = old.backend.native
    # Attach a unique, self-contained borderFill to the OLD charPr.
    borders = next(n for n in old_native.header_model.iter() if local_name(n.tag) == "borderFills")
    source = next(c for c in borders.children if local_name(c.tag) == "borderFill")
    imported = ElementModel.from_dict(source.to_dict())
    imported.set("id", "99")
    # make its semantic signature unique without creating external dependencies
    imported.set("shadow", "1" if imported.get("shadow") != "1" else "0")
    borders.children.append(imported)
    borders.set("itemCnt", str(len([c for c in borders.children if local_name(c.tag) == "borderFill"])))
    old_cp = old_native.styles.char_property(old.paragraphs[-1].runs[-1].element_model.get("charPrIDRef"))
    old_cp.set("borderFillIDRef", "99")

    out = tmp_path / "border-remap.hwpx"
    old.compare(new, author="QA", everywhere=False).save(out)
    assert validate_hwpx_file(out).ok
    header, _ = _roots(out)
    change = header.xpath('.//hh:trackChange[@type="CharShape"]', namespaces=NS)[0]
    old_charpr = header.xpath(f'.//hh:charPr[@id="{change.get("charshapeID")}"]', namespaces=NS)[0]
    border_id = old_charpr.get("borderFillIDRef")
    assert border_id and border_id != "99"
    border = header.xpath(f'.//hh:borderFill[@id="{border_id}"]', namespaces=NS)
    assert len(border) == 1
    assert border[0].get("shadow") == imported.get("shadow")


def test_validator_rejects_dangling_charpr_font_and_border_refs(tmp_path: Path):
    doc = Document.new("hwpx")
    p = doc.add_paragraph("Broken refs")
    native = doc.backend.native
    cp = native.styles.char_property(p.runs[0].element_model.get("charPrIDRef"))
    cp.set("borderFillIDRef", "999")
    font_ref = next(c for c in cp.children if local_name(c.tag) == "fontRef")
    font_ref.set("latin", "999")
    report = validate_document_model(native)
    codes = {issue.code for issue in report.issues}
    assert "charpr-borderfill-ref-missing" in codes
    assert "charpr-font-ref-missing" in codes


def test_embedded_old_font_dependency_fails_closed():
    old, new = _pair()
    native = old.backend.native
    cp = native.styles.char_property(old.paragraphs[-1].runs[-1].element_model.get("charPrIDRef"))
    ref = next(c for c in cp.children if local_name(c.tag) == "fontRef")
    fid = ref.get("latin")
    block = next(c for c in native.header_model.iter() if local_name(c.tag) == "fontface" and (c.get("lang") or "").upper() == "LATIN")
    font = next(c for c in block.children if local_name(c.tag) == "font" and c.get("id") == fid)
    font.set("isEmbedded", "1")
    try:
        old.compare(new, author="QA", everywhere=False)
    except DocumentUnsupportedError as exc:
        assert exc.code == "compare-hwpx-format-resource-dependency-unsupported"
    else:  # pragma: no cover
        raise AssertionError("embedded font import must fail closed")
