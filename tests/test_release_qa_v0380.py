"""v0.38.0 image-bullet cross-document release-QA integrity."""
from pathlib import Path
import hashlib, json
from zipfile import ZipFile

from lxml import etree
from pywpdoc._engine import validate_hwpx_file

ROOT = Path(__file__).resolve().parents[1]
HH = "http://www.hancom.co.kr/hwpml/2011/head"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
OPF = "http://www.idpf.org/2007/opf/"
NS = {"hh": HH, "hp": HP, "opf": OPF}


def test_v0380_image_bullet_manifest_and_files_are_consistent():
    idx = json.loads((ROOT / "docs/maintainers/QA_INDEX_V0380.json").read_text())
    assert idx["release"] == "0.38.0-candidate"
    item = idx["scenarios"][0]
    d = ROOT / "tests/fixtures/historical" / item["directory"]
    m = json.loads((d / "manifest.json").read_text())
    assert m["scenario_id"] == item["scenario_id"]
    assert m["status"] == "external-hancom-2020-gui-gate-pending"
    for role in ("old", "new", "tracked"):
        p = d / m[role]["file"]
        assert p.exists()
        assert hashlib.sha256(p.read_bytes()).hexdigest() == m[role]["sha256"]
        assert validate_hwpx_file(p).ok


def test_v0380_tracked_review_contains_both_image_bullet_payloads_and_remap():
    d = ROOT / "tests/fixtures/historical/qa_hwpx_image_bullet_v0380"
    m = json.loads((d / "manifest.json").read_text())
    p = d / m["tracked"]["file"]
    with ZipFile(p) as zf:
        h = etree.fromstring(zf.read("Contents/header.xml"))
        s = etree.fromstring(zf.read("Contents/section0.xml"))
        c = etree.fromstring(zf.read("Contents/content.hpf"))
        changes = h.xpath('.//hh:trackChange[@type="ParaShape"]', namespaces=NS)
        assert len(changes) == m["expected"]["count"] == 1
        para = s.xpath('.//hp:p[.//hp:t="Image bullet resource: Sample Text"]', namespaces=NS)[0]
        assert para.get("paraTcId") == changes[0].get("id")
        old_pp = h.xpath(f'.//hh:paraPr[@id="{changes[0].get("parashapeID")}"]', namespaces=NS)[0]
        new_pp = h.xpath(f'.//hh:paraPr[@id="{para.get("paraPrIDRef")}"]', namespaces=NS)[0]
        old_bid = old_pp.xpath('./hh:heading/@idRef', namespaces=NS)[0]
        new_bid = new_pp.xpath('./hh:heading/@idRef', namespaces=NS)[0]
        assert old_bid == m["expected"]["old_bullet_id"]
        assert new_bid == m["expected"]["new_bullet_id"]
        old_ref = h.xpath(f'.//hh:bullet[@id="{old_bid}"]/*[local-name()="img"]/@binaryItemIDRef', namespaces=NS)[0]
        new_ref = h.xpath(f'.//hh:bullet[@id="{new_bid}"]/*[local-name()="img"]/@binaryItemIDRef', namespaces=NS)[0]
        assert old_ref == m["expected"]["old_binary_item_id"]
        assert new_ref == m["expected"]["new_binary_item_id"]
        hrefs = {x.get("id"): x.get("href") for x in c.xpath('.//opf:manifest/opf:item', namespaces=NS)}
        assert hrefs[old_ref] == m["expected"]["old_binary_href"]
        assert hrefs[new_ref] == m["expected"]["new_binary_href"]
        assert hrefs[old_ref] in zf.namelist()
        assert hrefs[new_ref] in zf.namelist()
        assert zf.read(hrefs[old_ref]) != zf.read(hrefs[new_ref])
        assert not s.xpath('.//hp:insertBegin | .//hp:insertEnd | .//hp:deleteBegin | .//hp:deleteEnd', namespaces=NS)
