"""v0.17 section/story module isolation and backend-owned contract tests."""
from __future__ import annotations

import ast
from pathlib import Path
import zipfile

import pytest
from lxml import etree

from pywpdoc._engine.core import Mm, WD_ORIENT
from pywpdoc._engine.core.contracts import HeaderFooterBackend, SectionBackend
from pywpdoc._engine.core.errors import DocumentUnsupportedError

ROOT = Path(__file__).resolve().parents[1] / "src" / "pywpdoc" / "_engine"


def _backend_class(kind: str):
    if kind == "hwpx":
        from pywpdoc._engine.hwpx import Document
    else:
        from pywpdoc._engine.docx import Document
    return Document


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append("." * node.level + (node.module or ""))
    return names


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_section_and_story_modules_have_narrow_dependencies(kind: str):
    section = ROOT / kind / "section.py"
    story = ROOT / kind / "story.py"
    assert section.exists() and story.exists()
    opposite = f".{('docx' if kind == 'hwpx' else 'hwpx')}"
    for path in (section, story):
        imports = _imports(path)
        assert ".backend" not in imports
        assert not [name for name in imports if ".common" in name or opposite in name]
    # Section owns page/story routing, story owns content wrappers.  Reverse
    # story -> section import would create the maintenance cycle we want to avoid.
    assert ".story" in _imports(section)
    assert ".section" not in _imports(story)


def test_backend_modules_delegate_section_instead_of_owning_implementation():
    for kind in ("hwpx", "docx"):
        source = (ROOT / kind / "backend.py").read_text(encoding="utf-8")
        assert "class Section(" not in source
        assert "class HeaderFooter(" not in source
        if kind == "hwpx":
            # HWPX page/story defaults now live below the standalone wrapper.
            assert "from .section import Section" in source
            assert "configure_new_document_layout" not in source
        else:
            assert "from .section import Section, configure_new_document_layout" in source


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_section_and_story_public_types_are_backend_owned(kind: str):
    Document = _backend_class(kind)
    doc = Document.new()
    section = doc.sections[0]
    header = section.header
    assert type(section).__module__ == f"pywpdoc._engine.{kind}.section"
    assert type(header).__module__ == f"pywpdoc._engine.{kind}.story"
    assert isinstance(section, SectionBackend)
    assert isinstance(header, HeaderFooterBackend)
    assert all(type(p).__module__ == f"pywpdoc._engine.{kind}.paragraph" for p in header.paragraphs)


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_section_geometry_and_orientation_reopen(kind: str, tmp_path: Path):
    Document = _backend_class(kind)
    doc = Document.new()
    section = doc.sections[0]
    section.left_margin = Mm(17)
    section.right_margin = Mm(19)
    section.top_margin = Mm(16)
    section.bottom_margin = Mm(18)
    section.header_distance = Mm(8)
    section.footer_distance = Mm(9)
    section.orientation = WD_ORIENT.LANDSCAPE
    path = tmp_path / f"section-story.{kind}"
    doc.save(path)
    reopened = Document.open(path)
    section = reopened.sections[0]
    assert abs(section.left_margin.mm - 17.0) <= 0.03
    assert abs(section.right_margin.mm - 19.0) <= 0.03
    assert abs(section.header_distance.mm - 8.0) <= 0.03
    assert abs(section.footer_distance.mm - 9.0) <= 0.03
    assert section.orientation == WD_ORIENT.LANDSCAPE


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_header_footer_story_content_is_backend_owned(kind: str, tmp_path: Path):
    Document = _backend_class(kind)
    doc = Document.new()
    section = doc.sections[0]
    header = section.header
    header.text = "V017 Header"
    header.add_paragraph("second")
    table = header.add_table(1, 2, style="Table Grid")
    table.cell(0, 0).text = "A"
    table.cell(0, 1).text = "B"
    footer = section.footer
    footer.text = "V017 Footer"

    assert header.text == "V017 Header\nsecond"
    assert len(header.tables) == 1
    blocks = list(header.iter_inner_content())
    assert any(type(x).__module__ == f"pywpdoc._engine.{kind}.table" for x in blocks)

    path = tmp_path / f"story.{kind}"
    doc.save(path)
    reopened = Document.open(path)
    h2 = reopened.sections[0].header
    assert h2.text == "V017 Header\nsecond"
    assert h2.tables[0].cell(0, 0).text == "A"
    assert reopened.sections[0].footer.text == "V017 Footer"


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_even_header_is_operational_without_common(kind: str, tmp_path: Path):
    Document = _backend_class(kind)
    doc = Document.new()
    section = doc.sections[0]
    section.even_page_header.text = "EVEN"
    path = tmp_path / f"even.{kind}"
    doc.save(path)
    reopened = Document.open(path)
    assert reopened.sections[0].even_page_header.text == "EVEN"
    if kind == "docx":
        assert reopened.native.settings.odd_and_even_pages_header_footer is True


def test_first_page_header_support_remains_backend_specific():
    from pywpdoc._engine.docx import Document as DocxDocument
    from pywpdoc._engine.hwpx import Document as HwpxDocument
    docx = DocxDocument.new()
    docx.sections[0].first_page_header.text = "FIRST"
    assert docx.native.sections[0].different_first_page_header_footer is True

    hwpx = HwpxDocument.new()
    with pytest.raises(NotImplementedError):
        _ = hwpx.sections[0].first_page_header


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_header_table_defaults_to_section_content_width(kind: str, tmp_path: Path):
    Document = _backend_class(kind)
    doc = Document.new()
    section = doc.sections[0]
    section.left_margin = Mm(20)
    section.right_margin = Mm(20)
    table = section.header.add_table(1, 2, style="Table Grid")
    expected = section.page_width.mm - section.left_margin.mm - section.right_margin.mm
    actual = sum(column.width.mm for column in table.columns)
    assert abs(actual - expected) <= 0.08
    path = tmp_path / f"header-table-width.{kind}"
    doc.save(path)
    reopened = Document.open(path)
    actual2 = sum(column.width.mm for column in reopened.sections[0].header.tables[0].columns)
    assert abs(actual2 - expected) <= 0.08


def test_common_returns_backend_owned_section_and_story_types():
    from pywpdoc._engine.common import Document as CommonDocument
    for kind in ("hwpx", "docx"):
        direct = _backend_class(kind).new()
        common = CommonDocument.new(kind)
        assert type(common.sections[0]) is type(direct.sections[0])
        assert type(common.sections[0].header) is type(direct.sections[0].header)
        assert ".common" not in type(common.sections[0].header).__module__


def test_hwpx_story_mirror_remains_identical_after_backend_wrapper_save(tmp_path: Path):
    from pywpdoc._engine.hwpx import Document
    doc = Document.new()
    doc.sections[0].header.text = "mirror"
    out = tmp_path / "mirror.hwpx"
    doc.save(out)
    hp = "http://www.hancom.co.kr/hwpml/2011/paragraph"
    with zipfile.ZipFile(out) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
    headers = root.xpath(".//hp:header[@applyPageType='BOTH']", namespaces={"hp": hp})
    assert len(headers) == 2
    assert etree.tostring(headers[0], method="c14n") == etree.tostring(headers[1], method="c14n")

@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_add_section_returns_backend_owned_section(kind: str, tmp_path: Path):
    Document = _backend_class(kind)
    doc = Document.new()
    second = doc.add_section()
    assert type(second).__module__ == f"pywpdoc._engine.{kind}.section"
    assert len(doc.sections) == 2
    second.left_margin = Mm(21)
    out = tmp_path / f"two-sections.{kind}"
    doc.save(out)
    reopened = Document.open(out)
    assert len(reopened.sections) == 2
    assert type(reopened.sections[1]).__module__ == f"pywpdoc._engine.{kind}.section"
    assert abs(reopened.sections[1].left_margin.mm - 21.0) <= 0.03

def test_persisted_header_table_width_matches_cross_format_contract(tmp_path: Path):
    from pywpdoc._engine.hwpx import Document as HwpxDocument
    from pywpdoc._engine.docx import Document as DocxDocument

    outputs = {}
    for kind, Document in (("hwpx", HwpxDocument), ("docx", DocxDocument)):
        doc = Document.new()
        section = doc.sections[0]
        section.left_margin = Mm(18)
        section.right_margin = Mm(20)
        section.header.add_table(1, 2, style="Table Grid")
        out = tmp_path / f"persisted-header.{kind}"
        doc.save(out)
        outputs[kind] = out

    hp = "http://www.hancom.co.kr/hwpml/2011/paragraph"
    with zipfile.ZipFile(outputs["hwpx"]) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
    page = root.xpath(".//hp:pagePr", namespaces={"hp": hp})[0]
    margin = page.xpath("./hp:margin", namespaces={"hp": hp})[0]
    h_body = (int(page.get("width")) - int(margin.get("left")) - int(margin.get("right"))) * 25.4 / 7200
    h_tbl = root.xpath(".//hp:secPr/hp:header[@applyPageType='BOTH']//hp:tbl/hp:sz", namespaces={"hp": hp})[0]
    h_table = int(h_tbl.get("width")) * 25.4 / 7200

    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    with zipfile.ZipFile(outputs["docx"]) as zf:
        document = etree.fromstring(zf.read("word/document.xml"))
        header_name = next(name for name in zf.namelist() if name.startswith("word/header") and name.endswith(".xml"))
        header = etree.fromstring(zf.read(header_name))
    ns = {"w": w}
    sect = document.xpath(".//w:sectPr", namespaces=ns)[-1]
    pg = sect.xpath("./w:pgSz", namespaces=ns)[0]
    mar = sect.xpath("./w:pgMar", namespaces=ns)[0]
    twip_mm = lambda value: int(value) * 25.4 / 1440
    d_body = twip_mm(pg.get(f"{{{w}}}w")) - twip_mm(mar.get(f"{{{w}}}left")) - twip_mm(mar.get(f"{{{w}}}right"))
    grid = header.xpath(".//w:tbl[1]/w:tblGrid/w:gridCol", namespaces=ns)
    d_table = sum(twip_mm(col.get(f"{{{w}}}w")) for col in grid)

    assert abs(h_body - h_table) <= 0.08
    assert abs(d_body - d_table) <= 0.08
    assert abs(h_table - d_table) <= 0.08
