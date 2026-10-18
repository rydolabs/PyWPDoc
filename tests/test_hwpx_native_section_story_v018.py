"""v0.18 regression gates for lowering HWPX section/story behavior."""
from __future__ import annotations

import ast
from pathlib import Path
import zipfile

from lxml import etree

from pywpdoc._engine.core import defaults
from pywpdoc._engine.core.units import Mm
from pywpdoc._engine.document import Document as NativeHwpxDocument
from pywpdoc._engine.hwpx import Document as HwpxDocument

ROOT = Path(__file__).resolve().parents[1] / "src" / "pywpdoc" / "_engine"


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append("." * node.level + (node.module or ""))
    return names


def test_hwpx_section_story_wrappers_are_thin_adapters():
    section_source = (ROOT / "hwpx" / "section.py").read_text(encoding="utf-8")
    story_source = (ROOT / "hwpx" / "story.py").read_text(encoding="utf-8")
    for forbidden in ("core.defaults", "core.units", "table_geometry", "local_name", "configure_table"):
        assert forbidden not in section_source
        assert forbidden not in story_source
    assert "_content_width" not in story_source
    assert "iter_inner_content()" in story_source  # object wrapping only
    assert "self.native.add_table" in story_source
    assert "self.native.text" in story_source


def test_native_hwpx_new_owns_default_page_layout():
    doc = NativeHwpxDocument.new()
    sec = doc.sections[0]
    assert abs(sec.page_width.mm - defaults.PAGE_WIDTH_MM) <= 0.03
    assert abs(sec.page_height.mm - defaults.PAGE_HEIGHT_MM) <= 0.03
    assert abs(sec.left_margin.mm - defaults.LEFT_MARGIN_MM) <= 0.03
    assert abs(sec.right_margin.mm - defaults.RIGHT_MARGIN_MM) <= 0.03
    assert abs(sec.top_margin.mm - defaults.TOP_MARGIN_MM) <= 0.03
    assert abs(sec.bottom_margin.mm - defaults.BOTTOM_MARGIN_MM) <= 0.03
    assert abs(sec.header_distance.mm - defaults.HEADER_DISTANCE_MM) <= 0.03
    assert abs(sec.footer_distance.mm - defaults.FOOTER_DISTANCE_MM) <= 0.03


def test_native_story_text_excludes_nested_table_text_but_all_text_keeps_it():
    doc = NativeHwpxDocument.new()
    header = doc.sections[0].header
    header.text = "Header line"
    table = header.add_table(1, 1, style="Table Grid")
    table.cell(0, 0).text = "CELL-TEXT"
    assert header.text == "Header line"
    assert "CELL-TEXT" in header.all_text


def test_native_story_table_owns_width_margins_and_vertical_alignment():
    doc = NativeHwpxDocument.new()
    sec = doc.sections[0]
    sec.left_margin = Mm(18)
    sec.right_margin = Mm(20)
    table = sec.header.add_table(1, 2, style="Table Grid")
    assert abs(sum(col.width.mm for col in table.columns) - sec.content_width * 25.4 / 7200) <= 0.08
    for cell in table.rows[0].physical_cells:
        assert cell.vertical_alignment.name == "TOP"
    margin = next(c for c in table.element_model.children if etree.QName(c.tag).localname == "inMargin")
    assert int(margin.get("left")) == int(Mm(defaults.CELL_MARGIN_LEFT_MM))
    assert int(margin.get("right")) == int(Mm(defaults.CELL_MARGIN_RIGHT_MM))


def test_native_created_story_uses_hwpx_header_style_baseline(tmp_path: Path):
    doc = NativeHwpxDocument.new()
    doc.sections[0].header.text = "Header"
    doc.sections[0].footer.text = "Footer"
    out = tmp_path / "story-style.hwpx"
    doc.save(out)
    hp = "http://www.hancom.co.kr/hwpml/2011/paragraph"
    with zipfile.ZipFile(out) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
    ns = {"hp": hp}
    for kind in ("header", "footer"):
        p = root.xpath(f".//hp:secPr/hp:{kind}[@applyPageType='BOTH']/hp:subList/hp:p[1]", namespaces=ns)[0]
        run = p.xpath("./hp:run[1]", namespaces=ns)[0]
        # The bundled real-Hancom skeleton's story style is id 14 / paraPr 9 / charPr 2.
        assert p.get("styleIDRef") == "14"
        assert p.get("paraPrIDRef") == "9"
        assert run.get("charPrIDRef") == "2"


def test_standalone_hwpx_story_is_only_an_adapter_over_native_behavior(tmp_path: Path):
    doc = HwpxDocument.new()
    sec = doc.sections[0]
    sec.left_margin = Mm(18)
    sec.right_margin = Mm(20)
    sec.header.text = "Header"
    table = sec.header.add_table(1, 2, style="Table Grid")
    table.cell(0, 0).text = "A"
    table.cell(0, 1).text = "B"
    out = tmp_path / "adapter.hwpx"
    doc.save(out)
    reopened = HwpxDocument.open(out)
    assert reopened.sections[0].header.text == "Header"
    assert reopened.sections[0].header.tables[0].cell(0, 0).text == "A"
    assert abs(sum(c.width.mm for c in reopened.sections[0].header.tables[0].columns) - 172.0) <= 0.08

def test_story_specific_first_paragraph_style_matches_cross_format_intent(tmp_path: Path):
    from pywpdoc._engine.docx import Document as DocxDocument

    hp_doc = HwpxDocument.new()
    dx_doc = DocxDocument.new()
    for doc in (hp_doc, dx_doc):
        sec = doc.sections[0]
        sec.header.text = "H1"
        sec.header.add_paragraph("H2")
        sec.footer.text = "F1"
    hp_path = tmp_path / "story-style.hwpx"
    dx_path = tmp_path / "story-style.docx"
    hp_doc.save(hp_path); dx_doc.save(dx_path)

    hp = "http://www.hancom.co.kr/hwpml/2011/paragraph"
    with zipfile.ZipFile(hp_path) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
    ns = {"hp": hp}
    hps = root.xpath(".//hp:secPr/hp:header[@applyPageType='BOTH']/hp:subList/hp:p", namespaces=ns)
    fps = root.xpath(".//hp:secPr/hp:footer[@applyPageType='BOTH']/hp:subList/hp:p", namespaces=ns)
    assert hps[0].get("styleIDRef") == "14"
    assert hps[1].get("styleIDRef") == "0"
    assert fps[0].get("styleIDRef") == "14"

    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    with zipfile.ZipFile(dx_path) as zf:
        header_name = next(n for n in zf.namelist() if n.startswith("word/header") and n.endswith(".xml"))
        footer_name = next(n for n in zf.namelist() if n.startswith("word/footer") and n.endswith(".xml"))
        hdr = etree.fromstring(zf.read(header_name)); ftr = etree.fromstring(zf.read(footer_name))
    wns = {"w": w}
    header_ps = hdr.xpath("./w:p", namespaces=wns)
    footer_ps = ftr.xpath("./w:p", namespaces=wns)
    assert header_ps[0].xpath("./w:pPr/w:pStyle/@w:val", namespaces=wns) == ["Header"]
    assert not header_ps[1].xpath("./w:pPr/w:pStyle", namespaces=wns)
    assert footer_ps[0].xpath("./w:pPr/w:pStyle/@w:val", namespaces=wns) == ["Footer"]


def test_hwpx_native_policy_helpers_have_no_common_or_docx_dependency():
    for name in ("_hwpx_section.py", "_hwpx_story.py", "_hwpx_table.py"):
        imports = _imports(ROOT / name)
        assert not [item for item in imports if ".common" in item or ".docx" in item]


def test_rich_header_switches_text_height_to_auto() -> None:
    from pywpdoc._engine.hwpx import Document
    from pywpdoc._engine.core import Mm

    doc = Document.new()
    sec = doc.sections[0]
    sec.header_distance = Mm(8)
    header = sec.header
    header.text = "one line"
    sub = next(c for c in header.native.element_model.children if c.tag.endswith("subList"))
    assert sub.get("textHeight") == str(int(Mm(8)))

    header.add_paragraph("second line")
    assert sub.get("textHeight") == "0"


def test_header_table_keeps_rich_story_auto_height_after_save(tmp_path) -> None:
    from zipfile import ZipFile
    from lxml import etree
    from pywpdoc._engine.hwpx import Document
    from pywpdoc._engine.core import Mm

    out = tmp_path / "rich_header.hwpx"
    doc = Document.new()
    sec = doc.sections[0]
    sec.header_distance = Mm(8)
    header = sec.header
    header.text = "H1"
    header.add_paragraph("H2")
    table = header.add_table(1, 2, style="Table Grid")
    table.cell(0, 0).text = "A"
    table.cell(0, 1).text = "B"
    doc.add_paragraph("BODY")
    doc.save(out)

    with ZipFile(out) as zf:
        xml = etree.fromstring(zf.read("Contents/section0.xml"))
    ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
    logical = xml.xpath(".//hp:secPr/hp:header[@applyPageType='BOTH']/hp:subList", namespaces=ns)
    mirror = xml.xpath(".//hp:ctrl/hp:header[@applyPageType='BOTH']/hp:subList", namespaces=ns)
    assert logical and mirror
    assert logical[0].get("textHeight") == "0"
    assert mirror[0].get("textHeight") == "0"


def test_page_geometry_mutation_drops_stale_section_lineseg_cache():
    """Page geometry changes must not leave the bundled skeleton's old line cache."""
    doc = NativeHwpxDocument.new()
    sec = doc.sections[0]
    assert any(
        etree.QName(node.tag).localname.lower() == "linesegarray"
        for node in sec.element_model.iter()
    )

    sec.left_margin = Mm(18)

    assert not any(
        etree.QName(node.tag).localname.lower() == "linesegarray"
        for node in sec.element_model.iter()
    )



def test_rich_header_keeps_explicit_native_area_without_auto_fit(tmp_path: Path):
    """Rich HWPX stories use native semantics; save must not invent page geometry."""
    doc = HwpxDocument.new()
    sec = doc.sections[0]
    sec.top_margin = Mm(16)
    sec.header_distance = Mm(8)
    sec.header.text = "V0212 Header"
    sec.header.add_paragraph("Second header line")
    table = sec.header.add_table(1, 2, style="Table Grid")
    table.cell(0, 0).text = "Header A"
    table.cell(0, 1).text = "Header B"

    out = tmp_path / "rich-header-native-semantics.hwpx"
    doc.save(out)

    # HWPX native semantics are explicit: rich content may overflow a caller-
    # supplied header area. The engine must not guess a content height or add
    # sample-specific clearance to rewrite that geometry.
    assert abs(sec.header_distance.mm - 8.0) <= 0.03

    hp = "http://www.hancom.co.kr/hwpml/2011/paragraph"
    with zipfile.ZipFile(out) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
    ns = {"hp": hp}
    margin = root.xpath(".//hp:pagePr/hp:margin", namespaces=ns)[0]
    headers = root.xpath(".//hp:header[@applyPageType='BOTH']", namespaces=ns)
    assert int(margin.get("header")) == int(Mm(8))
    assert len(headers) == 2
    # Keep the independently verified v0.18.1 rich-story container behavior.
    assert all(h.xpath("./hp:subList", namespaces=ns)[0].get("textHeight") == "0" for h in headers)
    assert etree.tostring(headers[0], method="c14n") == etree.tostring(headers[1], method="c14n")
