"""v0.39.0 semantic named-style identity release-QA integrity."""
from pathlib import Path
import hashlib, json
from zipfile import ZipFile

from lxml import etree
from pywpdoc._engine import validate_hwpx_file

ROOT = Path(__file__).resolve().parents[1]
HH = "http://www.hancom.co.kr/hwpml/2011/head"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS = {"hh": HH, "hp": HP}


def test_v0390_style_identity_manifest_and_files_are_consistent():
    idx = json.loads((ROOT / "docs/maintainers/QA_INDEX_V0390.json").read_text())
    assert idx["release"] == "0.39.0-candidate"
    item = idx["scenarios"][0]
    d = ROOT / "tests/fixtures/historical" / item["directory"]
    m = json.loads((d / "manifest.json").read_text())
    assert m["scenario_id"] == item["scenario_id"]
    assert m["status"] == "automated-contract-passed"
    for role in ("old", "new", "tracked"):
        p = d / m[role]["file"]
        assert p.exists()
        assert hashlib.sha256(p.read_bytes()).hexdigest() == m[role]["sha256"]
        assert validate_hwpx_file(p).ok


def test_v0390_tracked_review_keeps_new_local_style_id_and_tracks_only_parashape():
    d = ROOT / "tests/fixtures/historical/qa_hwpx_style_identity_v0390"
    m = json.loads((d / "manifest.json").read_text())
    p = d / m["tracked"]["file"]
    with ZipFile(p) as zf:
        h = etree.fromstring(zf.read("Contents/header.xml"))
        s = etree.fromstring(zf.read("Contents/section0.xml"))
    changes = h.xpath('.//hh:trackChange[@type="ParaShape"]', namespaces=NS)
    assert len(changes) == m["expected"]["count"] == 1
    assert not h.xpath('.//hh:trackChange[@type="CharShape"]', namespaces=NS)
    text = m["case"]["text"]
    para = s.xpath(f'.//hp:p[.//hp:t="{text}"]', namespaces=NS)[0]
    assert para.get("styleIDRef") == m["expected"]["new_local_style_id"]
    assert para.get("paraTcId") == changes[0].get("id")
    style = h.xpath('.//hh:style[@engName="Body"]', namespaces=NS)[0]
    assert style.get("id") == m["expected"]["new_local_style_id"]
    old_pp = h.xpath(f'.//hh:paraPr[@id="{changes[0].get("parashapeID")}"]', namespaces=NS)[0]
    new_pp = h.xpath(f'.//hh:paraPr[@id="{para.get("paraPrIDRef")}"]', namespaces=NS)[0]
    assert old_pp.xpath('./hh:lineSpacing/@value', namespaces=NS) == [str(m["expected"]["old_line_spacing_percent"])]
    assert new_pp.xpath('./hh:lineSpacing/@value', namespaces=NS) == [str(m["expected"]["new_line_spacing_percent"])]
    assert not s.xpath('.//hp:insertBegin | .//hp:insertEnd | .//hp:deleteBegin | .//hp:deleteEnd', namespaces=NS)
