"""Generate v0.35.0 cross-document HWPX CharShape release QA."""
from __future__ import annotations

import hashlib, json, sys
from pathlib import Path
from typing import Any
from zipfile import ZipFile
from lxml import etree

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pywpdoc import Document
from pywpdoc._engine import validate_hwpx_file

DATE = "2026-10-12T12:00:00Z"
AUTHOR = "user"
HH = "http://www.hancom.co.kr/hwpml/2011/head"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS = {"hh": HH, "hp": HP}
LANG_ATTRS = {"HANGUL":"hangul", "LATIN":"latin", "HANJA":"hanja", "JAPANESE":"japanese", "OTHER":"other", "SYMBOL":"symbol", "USER":"user"}
OLD_FONT = "PyWPDoc Legacy QA Font"
NEW_FONT = "PyWPDoc Modern QA Font"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _write(path: Path, data: dict[str, Any]):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

def _validate(path: Path):
    report = validate_hwpx_file(path)
    if not report.ok:
        raise RuntimeError(report.issues)
    Document.open(path)

def _font_faces(header, charpr):
    ref = charpr.xpath('./hh:fontRef', namespaces=NS)[0]
    faces = set()
    for lang, attr in LANG_ATTRS.items():
        fid = ref.get(attr)
        nodes = header.xpath(f'.//hh:fontface[@lang="{lang}"]/hh:font[@id="{fid}"]', namespaces=NS)
        if len(nodes) != 1:
            raise RuntimeError(f"unresolved font {lang}:{fid}")
        faces.add(nodes[0].get("face"))
    return faces


def generate_cross_document(root: Path) -> dict[str, Any]:
    out = root / "qa_hwpx_cross_document_char_format_v0350"
    out.mkdir(parents=True, exist_ok=True)
    old = Document.new("hwpx")
    new = Document.new("hwpx")

    op = old.add_paragraph(); op.add_run("Cross-document formatting: ")
    old_run = op.add_run("Alpha Beta"); old_run.font.name = OLD_FONT; old_run.font.size = 10
    np = new.add_paragraph(); np.add_run("Cross-document formatting: ")
    new_run = np.add_run("Alpha Beta"); new_run.font.name = NEW_FONT; new_run.font.size = 16; new_run.bold = True

    old_path = out / "crossdoc_old_v0350.hwpx"
    new_path = out / "crossdoc_new_v0350.hwpx"
    tracked_path = out / "crossdoc_tracked_review_v0350.hwpx"
    old.save(old_path); new.save(new_path)
    old.compare(new, author=AUTHOR, date=DATE, everywhere=False).save(tracked_path)
    for path in (old_path, new_path, tracked_path): _validate(path)

    with ZipFile(tracked_path) as zf:
        header = etree.fromstring(zf.read("Contents/header.xml"))
        section = etree.fromstring(zf.read("Contents/section0.xml"))
    change = header.xpath('.//hh:trackChange[@type="CharShape"]', namespaces=NS)
    if len(change) != 1:
        raise RuntimeError(f"expected one CharShape, got {len(change)}")
    change = change[0]
    old_cp = header.xpath(f'.//hh:charPr[@id="{change.get("charshapeID")}"]', namespaces=NS)[0]
    run = section.xpath('.//hp:run[hp:t="Alpha Beta"]', namespaces=NS)[0]
    new_cp = header.xpath(f'.//hh:charPr[@id="{run.get("charPrIDRef")}"]', namespaces=NS)[0]
    if _font_faces(header, old_cp) != {OLD_FONT} or _font_faces(header, new_cp) != {NEW_FONT}:
        raise RuntimeError("cross-document font remap contract failed")
    if run.get("paraTcId") != change.get("id") or run.get("charTcId") is not None:
        raise RuntimeError("native CharShape anchor contract failed")

    manifest = {
        "schema": "pywpdoc-release-qa/v1",
        "release": "0.35.0",
        "scenario_id": "hwpx-cross-document-char-format-resource-import",
        "status": "supported-gui-verification-required",
        "format": "hwpx",
        "purpose": "OLD-only font resources are imported/remapped into the NEW-derived review package.",
        "old_font": OLD_FONT,
        "new_font": NEW_FONT,
        "old": {"file": old_path.name, "sha256": _sha(old_path)},
        "new": {"file": new_path.name, "sha256": _sha(new_path)},
        "tracked": {"file": tracked_path.name, "sha256": _sha(tracked_path), "charshapeID": change.get("charshapeID"), "paraTcId": run.get("paraTcId")},
        "expected_accept_all": "NEW: modern font, 16pt, bold",
        "expected_reject_all": "OLD: legacy font, 10pt, normal",
        "gui_verification_required": True,
    }
    _write(out / "manifest.json", manifest)
    return manifest


def generate_all(root: Path):
    root = root.resolve()
    cross = generate_cross_document(root)
    index = {
        "schema": "pywpdoc-release-qa-index/v1", "release": "0.35.0",
        "scenarios": [{"scenario_id": cross["scenario_id"], "directory": "qa_hwpx_cross_document_char_format_v0350", "tracked_file_expected": True}],
    }
    _write(root / "QA_INDEX_V0350.json", index)

if __name__ == "__main__": generate_all(Path(__file__).resolve().parents[1])
