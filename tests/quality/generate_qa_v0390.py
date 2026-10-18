"""Generate v0.39.0 semantic named-style identity HWPX QA artifacts."""
from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lxml import etree

from pywpdoc import Document
from pywpdoc._engine import validate_hwpx_file
from pywpdoc._engine.model import local_name

TEXT = "Style-local-ID semantic identity: Sample Text"
DATE = "2026-10-12T13:50:00Z"
HH = "http://www.hancom.co.kr/hwpml/2011/head"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS = {"hh": HH, "hp": HP}


def _swap_style_ids(doc: Document, a: str = "1", b: str = "22") -> None:
    native = doc.backend.native
    mapping = {a: b, b: a}
    for section in native.section_models:
        for node in section.iter():
            ref = node.get("styleIDRef")
            if ref in mapping:
                node.set("styleIDRef", mapping[ref])
    styles = next(n for n in native.header_model.iter() if local_name(n.tag) == "styles")
    style_nodes = [c for c in styles.children if local_name(c.tag) == "style"]
    for node in style_nodes:
        old_id = node.get("id") or "0"
        if old_id in mapping:
            node.set("id", mapping[old_id])
        nxt = node.get("nextStyleIDRef")
        if nxt in mapping:
            node.set("nextStyleIDRef", mapping[nxt])
    style_nodes.sort(key=lambda n: int(n.get("id") or "0"))
    other = [c for c in styles.children if local_name(c.tag) != "style"]
    styles.children[:] = style_nodes + other


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    old = Document.new("hwpx")
    new = Document.new("hwpx")
    old.add_paragraph(TEXT, style="Body").paragraph_format.line_spacing_percent = 177
    new.add_paragraph(TEXT, style="Body").paragraph_format.line_spacing_percent = 190
    _swap_style_ids(new)

    old_path = root / "style_identity_old_v0390.hwpx"
    new_path = root / "style_identity_new_v0390.hwpx"
    tracked_path = root / "style_identity_tracked_review_v0390.hwpx"
    old.save(old_path)
    new.save(new_path)
    old.compare(new, author="PyWPDoc QA", date=DATE, everywhere=False).save(tracked_path)
    for path in (old_path, new_path, tracked_path):
        result = validate_hwpx_file(path)
        if not result.ok:
            raise RuntimeError(f"validation failed for {path}: {result.issues}")

    with ZipFile(tracked_path) as zf:
        header = etree.fromstring(zf.read("Contents/header.xml"))
        section = etree.fromstring(zf.read("Contents/section0.xml"))
    changes = header.xpath('.//hh:trackChange[@type="ParaShape"]', namespaces=NS)
    para = section.xpath(f'.//hp:p[.//hp:t="{TEXT}"]', namespaces=NS)[0]
    if len(changes) != 1 or para.get("styleIDRef") != "22" or para.get("paraTcId") != changes[0].get("id"):
        raise RuntimeError("unexpected v0.39.0 QA revision structure")

    manifest = {
        "scenario_id": "hwpx-semantic-style-identity-v0390",
        "release": "0.39.0-candidate",
        "status": "automated-contract-passed",
        "basis": [
            "HWPX style ids are header-local and can differ across unrelated documents",
            "named-style identity changes remain fail-closed because verified TrackChange records restore CharShape/ParaShape, not style identity",
            "v0.39.0 compares resolved named-style identity before deciding whether ParaShape tracking is safe",
        ],
        "old": {"file": old_path.name, "sha256": _sha(old_path), "body_style_id": "1", "line_spacing_percent": 177},
        "new": {"file": new_path.name, "sha256": _sha(new_path), "body_style_id": "22", "line_spacing_percent": 190},
        "tracked": {"file": tracked_path.name, "sha256": _sha(tracked_path), "body_style_id": "22"},
        "expected": {
            "track_change_type": "ParaShape", "count": 1,
            "body_anchor": "hp:p@paraTcId", "old_shape_attribute": "parashapeID",
            "old_line_spacing_percent": 177, "new_line_spacing_percent": 190,
            "current_style_name": "본문", "current_style_eng_name": "Body",
            "old_local_style_id": "1", "new_local_style_id": "22",
            "text_insert_delete_markers": 0,
        },
        "case": {"text": TEXT, "purpose": "same semantic Body style, different local style ids, plus ParaShape line-spacing change"},
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    index = {"release": "0.39.0-candidate", "scenarios": [{
        "scenario_id": manifest["scenario_id"], "directory": root.name, "status": manifest["status"],
    }]}
    (root.parent / "QA_INDEX_V0390.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    generate(Path(__file__).resolve().parents[1] / "qa_hwpx_style_identity_v0390")
