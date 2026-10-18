from pathlib import Path
from zipfile import ZipFile
from lxml import etree

from pywpdoc._engine import Document, reverse_hwpx, Pt
from pywpdoc._engine.model import local_name

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "fixtures" / "original_notice.hwpx"


def c14n(data: bytes) -> bytes:
    return etree.tostring(etree.fromstring(data), method="c14n")


def assert_same_payloads(a: Path, b: Path) -> None:
    with ZipFile(a) as za, ZipFile(b) as zb:
        assert za.namelist() == zb.namelist()
        for name in za.namelist():
            x, y = za.read(name), zb.read(name)
            if name.endswith((".xml", ".hpf", ".rdf")):
                assert c14n(x) == c14n(y), name
            else:
                assert x == y, name


def test_reverse_rebuild_without_document_specific_template(tmp_path: Path):
    model_dir = tmp_path / "model"
    model = reverse_hwpx(SOURCE, model_dir)
    doc = Document.from_reverse_model(model)
    out = tmp_path / "rebuilt.hwpx"
    doc.save(out)
    assert_same_payloads(SOURCE, out)


def test_typed_surface_counts():
    doc = Document.open(SOURCE)
    assert len(doc.all_paragraphs) == 52
    assert sum(len(p.runs) for p in doc.all_paragraphs) == 96
    assert len(doc.tables) == 2
    assert len(doc.all_tables) == 3
    assert sum(len(row.physical_cells) for table in doc.all_tables for row in table.rows) == 20
    assert len(doc.rectangles) == 3
    assert len(doc.pictures) == 1


def test_typed_edits_preserve_structure(tmp_path: Path):
    doc = Document.open(SOURCE)
    doc.paragraphs[5].runs[0].text = "2027. 9. 23."
    doc.tables[1].cell(0, 0).text = "학년 / 반"
    assert doc.replace_text("2026년 쓰담 달리기 참여", "2027년 쓰담 달리기 참여") == 2

    out = tmp_path / "edited.hwpx"
    doc.save(out)
    reopened = Document.open(out)

    assert reopened.paragraphs[5].runs[0].text == "2027. 9. 23."
    assert reopened.tables[1].cell(0, 0).text == "학년 / 반"
    assert "2027년 쓰담 달리기 참여" in "".join(p.text for p in reopened.all_paragraphs)
    assert len(reopened.tables) == 2
    assert len(reopened.all_tables) == 3
    assert len(reopened.rectangles) == 3
    assert len(reopened.pictures) == 1


def test_new_document_add_paragraph(tmp_path: Path):
    doc = Document.new()
    p = doc.add_paragraph("새 HWPX 문단")
    p.add_run(" + 추가 run", char_pr_id_ref="0")
    out = tmp_path / "new.hwpx"
    doc.save(out)

    reopened = Document.open(out)
    assert reopened.paragraphs[-1].text == "새 HWPX 문단 + 추가 run"
    with ZipFile(out) as zf:
        assert zf.read("mimetype") == b"application/hwp+zip"


def test_copy_on_write_run_font_paragraph_and_cell_border(tmp_path: Path):
    from pywpdoc._engine import Pt

    doc = Document.open(SOURCE)
    assert doc.styles.char_count == 61
    assert doc.styles.paragraph_count == 44
    assert doc.styles.border_fill_count == 20

    paragraph = doc.all_paragraphs[8]
    target = paragraph.runs[0]
    sibling = paragraph.runs[2]
    original_target_ref = target.char_pr_id_ref
    assert original_target_ref == sibling.char_pr_id_ref == "15"
    assert target.bold is False
    assert target.font.name == "함초롬바탕"
    assert target.font.size == Pt(12)
    assert paragraph.alignment == "JUSTIFY"
    assert paragraph.paragraph_format.line_spacing_percent == 190

    # Each setter derives from the run's current style. Intermediate COW ids are
    # allowed in memory, but save() must garbage-collect only those session ids
    # that are no longer referenced.
    target.bold = True
    target.font.size = Pt(13.5)
    target.font.color = "#336699"
    target.font.name = "나눔고딕"

    # The sibling shared the original id, so it must remain unchanged.
    assert sibling.char_pr_id_ref == "15"
    assert sibling.bold is False
    assert sibling.font.name == "함초롬바탕"
    assert target.char_pr_id_ref != original_target_ref
    assert target.bold is True
    assert target.font.size == Pt(13.5)
    assert target.font.color == "#336699"
    assert target.font.name == "나눔고딕"

    paragraph.alignment = "CENTER"
    paragraph.paragraph_format.line_spacing_percent = 150
    assert paragraph.alignment == "CENTER"
    assert paragraph.paragraph_format.line_spacing_percent == 150

    cell = doc.tables[1].cell(0, 0)
    original_border_ref = cell.border_fill_id_ref
    cell.border.color = "#7030A0"
    cell.border.width = "0.4 mm"
    cell.fill_color = "#FFF2CC"
    assert cell.border_fill_id_ref != original_border_ref
    assert cell.border.color == "#7030A0"
    assert cell.border.width == "0.4 mm"
    assert cell.fill_color == "#FFF2CC"

    out = tmp_path / "formatting.hwpx"
    doc.save(out)
    reopened = Document.open(out)

    p2 = reopened.all_paragraphs[8]
    target2, sibling2 = p2.runs[0], p2.runs[2]
    assert target2.bold is True
    assert target2.font.size == Pt(13.5)
    assert target2.font.color == "#336699"
    assert target2.font.name == "나눔고딕"
    assert sibling2.char_pr_id_ref == "15"
    assert sibling2.bold is False
    assert sibling2.font.name == "함초롬바탕"
    assert p2.alignment == "CENTER"
    assert p2.paragraph_format.line_spacing_percent == 150

    c2 = reopened.tables[1].cell(0, 0)
    assert c2.border.color == "#7030A0"
    assert c2.border.width == "0.4 mm"
    assert c2.fill_color == "#FFF2CC"

    # Compatibility rule: keep intermediate COW definitions so shared-style
    # ID spaces remain dense/index-like for Hancom. Existing definitions are
    # never renumbered or deleted.
    assert reopened.styles.char_count == 65
    assert reopened.styles.paragraph_count == 46
    assert reopened.styles.border_fill_count == 23


def test_same_format_assignment_reuses_existing_ids():
    doc = Document.open(SOURCE)
    paragraph = doc.all_paragraphs[8]
    run = paragraph.runs[0]
    cell = doc.tables[1].cell(0, 0)

    char_ref = run.char_pr_id_ref
    para_ref = paragraph.para_pr_id_ref
    border_ref = cell.border_fill_id_ref

    run.bold = False
    run.font.size = Pt(12)
    run.font.color = "#000000"
    paragraph.alignment = "JUSTIFY"
    paragraph.paragraph_format.line_spacing_percent = 190
    cell.border.color = "#000000"

    assert run.char_pr_id_ref == char_ref
    assert paragraph.para_pr_id_ref == para_ref
    assert cell.border_fill_id_ref == border_ref
    assert doc.styles.char_count == 61
    assert doc.styles.paragraph_count == 44
    assert doc.styles.border_fill_count == 20


def test_new_document_add_table_and_cell_formatting(tmp_path: Path):
    doc = Document.new()
    table = doc.add_table(2, 2, width=24000, height=4000)
    table.cell(0, 0).text = "항목"
    table.cell(0, 1).text = "값"
    table.cell(1, 0).text = "상태"
    table.cell(1, 1).text = "완료"
    table.cell(0, 0).fill_color = "#FFF2CC"
    table.cell(0, 0).border.color = "#7030A0"

    out = tmp_path / "table.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    created = reopened.tables[-1]
    assert (created.row_count, created.col_count) == (2, 2)
    assert created.cell(0, 0).text == "항목"
    assert created.cell(1, 1).text == "완료"
    assert created.cell(0, 0).fill_color == "#FFF2CC"
    assert created.cell(0, 0).border.color == "#7030A0"


def test_new_document_add_rectangle_textbox(tmp_path: Path):
    doc = Document.new()
    rect = doc.add_rectangle(
        24000, 6000, text="안내 상자", line_color="#7030A0", fill_color="#F4ECF7"
    )
    rect.add_paragraph("두 번째 문단")
    out = tmp_path / "rectangle.hwpx"
    doc.save(out)

    reopened = Document.open(out)
    rect2 = reopened.rectangles[-1]
    assert rect2.text == "안내 상자\n두 번째 문단"
    assert len(rect2.paragraphs) == 2


def test_new_document_add_picture_updates_manifest(tmp_path: Path):
    import base64

    # 1x1 transparent PNG
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    doc = Document.new()
    pic = doc.add_picture(png, "png", width=7200)
    assert pic.binary_item_id_ref == "image1"
    out = tmp_path / "picture.hwpx"
    doc.save(out)

    reopened = Document.open(out)
    assert reopened.pictures[-1].binary_item_id_ref == "image1"
    assert reopened.pictures[-1].size == (7200, 7200)
    with ZipFile(out) as zf:
        assert zf.read("BinData/image1.png") == png
        hpf = etree.fromstring(zf.read("Contents/content.hpf"))
        items = [e for e in hpf.iter() if etree.QName(e.tag).localname == "item"]
        image = next(e for e in items if e.get("id") == "image1")
        assert image.get("href") == "BinData/image1.png"
        assert image.get("media-type") == "image/png"


def test_page_setup_typed_api(tmp_path: Path):
    from pywpdoc._engine import Mm

    source = Document.open(SOURCE)
    assert source.page_setup.width == 59528
    assert source.page_setup.height == 84186
    assert source.page_setup.left_margin == 5669
    assert source.page_setup.top_margin == 4252

    doc = Document.new()
    doc.page_setup.left_margin = Mm(20)
    doc.page_setup.right_margin = Mm(20)
    doc.page_setup.top_margin = Mm(15)
    doc.page_setup.bottom_margin = Mm(15)
    doc.page_setup.header_distance = 0
    doc.page_setup.footer_distance = 0
    out = tmp_path / "page-setup.hwpx"
    doc.save(out)

    reopened = Document.open(out)
    assert reopened.page_setup.left_margin == Mm(20)
    assert reopened.page_setup.right_margin == Mm(20)
    assert reopened.page_setup.top_margin == Mm(15)
    assert reopened.page_setup.bottom_margin == Mm(15)
    assert reopened.page_setup.header_distance == 0
    assert reopened.page_setup.footer_distance == 0


def test_styles_collection_and_paragraph_style(tmp_path: Path):
    doc = Document.open(SOURCE)
    assert doc.styles.style_count == 25
    normal = doc.styles["바탕글"]
    assert normal.id == "0"
    assert doc.styles[0].name == "바탕글"
    assert doc.styles["Normal"].id == "0"
    assert "본문" in doc.styles.names()

    paragraph = doc.paragraphs[1]
    paragraph.style = "본문"
    assert paragraph.style is not None
    assert paragraph.style.name == "본문"
    assert paragraph.style_id_ref == "1"
    assert paragraph.para_pr_id_ref == doc.styles["본문"].para_pr_id_ref

    out = tmp_path / "style-assignment.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    assert reopened.paragraphs[1].style.name == "본문"


def test_table_add_row_column_and_merge(tmp_path: Path):
    doc = Document.new()
    table = doc.add_table(2, 2, width=20000, height=4000)
    table.cell(0, 0).text = "A"
    table.cell(0, 1).text = "B"
    table.cell(1, 0).text = "C"
    table.cell(1, 1).text = "D"

    new_row = table.add_row(height=2500)
    assert table.row_count == 3
    assert len(new_row.cells) == 2
    new_row[0].text = "E"
    new_row[1].text = "F"

    new_col = table.add_column(width=5000)
    assert table.col_count == 3
    assert len(new_col) == 3
    table.cell(0, 2).text = "G"

    merged = table.merge_cells(0, 0, 1, 1)
    assert merged.address == (0, 0)
    assert merged.span == (2, 2)
    # Covered coordinates resolve to the anchor, like python-docx merged cells.
    assert table.cell(1, 1).element_model is merged.element_model
    assert "A" in merged.text and "D" in merged.text

    out = tmp_path / "table-structure.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    t2 = reopened.tables[-1]
    assert (t2.row_count, t2.col_count) == (3, 3)
    assert t2.cell(0, 0).span == (2, 2)
    assert t2.cell(1, 1).address == (0, 0)
    assert t2.cell(2, 2).address == (2, 2)


def test_shape_position_wrap_and_resize(tmp_path: Path):
    import base64

    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    doc = Document.new()
    rect = doc.add_rectangle(10000, 5000, text="box", treat_as_char=False)
    rect.resize(width=12000, height=7000)
    rect.set_position(
        treat_as_char=False,
        horizontal_alignment="CENTER",
        vertical_alignment="TOP",
        horizontal_offset=1000,
        vertical_offset=1500,
        horizontal_relative_to="PAGE",
        vertical_relative_to="PAGE",
        text_wrap="TOP_AND_BOTTOM",
    )
    assert (rect.width, rect.height) == (12000, 7000)
    assert rect.text_wrap == "TOP_AND_BOTTOM"
    assert rect.treat_as_char is False
    assert rect.horizontal_offset == 1000

    pic = doc.add_picture(png, "png", width=6000)
    pic.width = 8000
    pic.height = 4000
    pic.horizontal_alignment = "RIGHT"
    pic.text_wrap = "SQUARE"
    assert pic.size == (8000, 4000)

    out = tmp_path / "shapes.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    r2 = reopened.rectangles[-1]
    p2 = reopened.pictures[-1]
    assert (r2.width, r2.height) == (12000, 7000)
    assert r2.horizontal_alignment == "CENTER"
    assert r2.vertical_offset == 1500
    assert r2.text_wrap == "TOP_AND_BOTTOM"
    assert p2.size == (8000, 4000)
    assert p2.horizontal_alignment == "RIGHT"


def test_header_footer_simple_story_roundtrip(tmp_path: Path):
    doc = Document.new()
    section = doc.sections[0]
    section.set_header_text("학교 가정통신문", page_type="BOTH")
    section.set_footer_text("문의: 교무실", page_type="ODD")
    assert section.header.text == "학교 가정통신문"
    assert section.get_footer("ODD").text == "문의: 교무실"

    # Editing through the object updates both the logical secPr story and the
    # hp:ctrl mirror that Hancom actually reads.
    section.header.text = "수정된 머리말"

    out = tmp_path / "header-footer.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    sec2 = reopened.sections[0]
    assert sec2.get_header("BOTH").text == "수정된 머리말"
    assert sec2.get_footer("ODD").text == "문의: 교무실"

    with ZipFile(out) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
        hp = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
        logical_headers = root.findall(f".//{hp}secPr/{hp}header")
        control_headers = root.findall(f".//{hp}ctrl/{hp}header")
        assert len(logical_headers) == 1
        assert len(control_headers) == 1
        assert "".join(logical_headers[0].itertext()) == "수정된 머리말"
        assert "".join(control_headers[0].itertext()) == "수정된 머리말"


def test_multi_section_package_manifest_and_roundtrip(tmp_path: Path):
    doc = Document.new()
    doc.sections[0].add_paragraph("첫 번째 절")
    second = doc.add_section()
    second.add_paragraph("두 번째 절")
    second.page_setup.left_margin = 7000

    out = tmp_path / "multi-section.hwpx"
    doc.save(out)
    reopened = Document.open(out)

    assert len(reopened.sections) == 2
    assert "첫 번째 절" in "".join(p.text for p in reopened.sections[0].paragraphs)
    assert "두 번째 절" in "".join(p.text for p in reopened.sections[1].paragraphs)
    assert reopened.sections[1].page_setup.left_margin == 7000

    with ZipFile(out) as zf:
        assert "Contents/section0.xml" in zf.namelist()
        assert "Contents/section1.xml" in zf.namelist()
        header = etree.fromstring(zf.read("Contents/header.xml"))
        assert header.get("secCnt") == "2"
        content = etree.fromstring(zf.read("Contents/content.hpf"))
        items = [(e.get("id"), e.get("href")) for e in content.iter() if etree.QName(e.tag).localname == "item"]
        refs = [e.get("idref") for e in content.iter() if etree.QName(e.tag).localname == "itemref"]
        assert ("section0", "Contents/section0.xml") in items
        assert ("section1", "Contents/section1.xml") in items
        assert refs.count("section0") == 1 and refs.count("section1") == 1


def test_reverse_roundtrip_multi_section(tmp_path: Path):
    source = tmp_path / "source-multi.hwpx"
    doc = Document.new()
    doc.sections[0].add_paragraph("A절")
    s2 = doc.add_section()
    s2.add_paragraph("B절")
    doc.save(source)

    model = reverse_hwpx(source, tmp_path / "reverse-multi")
    rebuilt = tmp_path / "rebuilt-multi.hwpx"
    Document.from_reverse_model(model).save(rebuilt)
    assert_same_payloads(source, rebuilt)


def test_rich_header_footer_runs_paragraphs_and_page_number(tmp_path: Path):
    doc = Document.new()
    header = doc.sections[0].header
    header.text = "가정통신문"
    header.add_run(" · 2026", bold=True)
    second = header.add_paragraph("페이지 ")
    header.add_page_number_field(paragraph=second, position="TOP_RIGHT", format_type="DIGIT")

    out = tmp_path / "rich-header.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    h2 = reopened.sections[0].get_header("BOTH")
    assert h2 is not None
    assert "가정통신문" in h2.text
    assert "2026" in h2.text
    assert len(h2.paragraphs) == 2

    with ZipFile(out) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
        hp = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
        logical = root.find(f".//{hp}secPr/{hp}header")
        mirror = root.find(f".//{hp}ctrl/{hp}header")
        assert logical is not None and mirror is not None
        assert etree.tostring(logical, method="c14n") == etree.tostring(mirror, method="c14n")
        assert logical.find(f".//{hp}pageNum") is not None
        assert logical.find(f".//{hp}autoNum[@numType='PAGE']") is not None


def test_footnote_endnote_typed_api(tmp_path: Path):
    doc = Document.new()
    paragraph = doc.add_paragraph("본문")
    foot = paragraph.add_footnote("각주 내용")
    foot.add_run(" 강조", bold=True)
    end = paragraph.add_endnote("미주 내용")

    assert foot.number == 1
    assert end.number == 1
    assert "각주 내용" in foot.text
    assert "미주 내용" in end.text

    out = tmp_path / "notes.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    p2 = next(p for p in reopened.paragraphs if p.text.startswith("본문"))
    assert len(p2.footnotes) == 1
    assert len(p2.endnotes) == 1
    assert "각주 내용" in p2.footnotes[0].text
    assert "강조" in p2.footnotes[0].text
    assert p2.endnotes[0].number == 1

    with ZipFile(out) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
        hp = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
        foot_el = root.find(f".//{hp}footNote")
        end_el = root.find(f".//{hp}endNote")
        assert foot_el is not None and end_el is not None
        assert foot_el.find(f".//{hp}autoNum[@numType='FOOTNOTE']") is not None
        assert end_el.find(f".//{hp}autoNum[@numType='ENDNOTE']") is not None


def test_bullet_and_numbered_list_authoring(tmp_path: Path):
    doc = Document.new()
    bullet = doc.add_list_paragraph("글머리표 항목", kind="bullet")
    numbered = doc.add_list_paragraph(
        "번호 항목",
        kind="number",
        level=1,
        levels=[{"format": "DIGIT", "text": "^1."}, {"format": "HANGUL_SYLLABLE", "text": "^2)"}],
    )
    assert bullet.para_pr_id_ref != "0"
    assert numbered.para_pr_id_ref != "0"

    out = tmp_path / "lists.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    bullet2 = next(p for p in reopened.paragraphs if p.text == "글머리표 항목")
    numbered2 = next(p for p in reopened.paragraphs if p.text == "번호 항목")
    bp = reopened.styles.paragraph_property(bullet2.para_pr_id_ref)
    np = reopened.styles.paragraph_property(numbered2.para_pr_id_ref)
    bhead = next(c for c in bp.children if local_name(c.tag) == "heading")
    nhead = next(c for c in np.children if local_name(c.tag) == "heading")
    assert bhead.get("type") == "BULLET" and bhead.get("level") == "0"
    assert nhead.get("type") == "NUMBER" and nhead.get("level") == "1"

    with ZipFile(out) as zf:
        header = etree.fromstring(zf.read("Contents/header.xml"))
        hh = "{http://www.hancom.co.kr/hwpml/2011/head}"
        assert header.find(f".//{hh}bullets/{hh}bullet") is not None
        defs = header.findall(f".//{hh}numberings/{hh}numbering")
        assert len(defs) >= 2


def test_append_row_and_column_after_merge(tmp_path: Path):
    doc = Document.new()
    table = doc.add_table(2, 3, width=30000, height=4000)
    table.cell(0, 0).text = "A"
    table.cell(0, 1).text = "B"
    table.merge_cells(0, 0, 1, 1)

    row = table.add_row(height=1800)
    row[0].text = "새 행"
    column = table.add_column(width=4500)
    column[0].text = "새 열"

    assert (table.row_count, table.col_count) == (3, 4)
    assert table.cell(1, 1).address == (0, 0)
    assert table.cell(2, 0).text == "새 행"
    assert table.cell(0, 3).text == "새 열"

    out = tmp_path / "merged-append.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    t2 = reopened.tables[-1]
    assert (t2.row_count, t2.col_count) == (3, 4)
    assert t2.cell(1, 1).address == (0, 0)
    assert t2.cell(2, 0).text == "새 행"
    assert t2.cell(0, 3).text == "새 열"


def test_insert_middle_row_and_column_extend_merges(tmp_path: Path):
    doc = Document.new()
    table = doc.add_table(3, 3, width=30000, height=6000)
    table.cell(0, 0).text = "ANCHOR"
    table.cell(1, 2).text = "old-r1-c2"
    table.merge_cells(0, 0, 1, 1)

    inserted = table.insert_row(1, height=1500)
    assert table.row_count == 4
    assert table.cell(0, 0).span == (3, 2)
    assert table.cell(1, 1).address == (0, 0)
    assert table.cell(2, 2).text == "old-r1-c2"
    assert len(inserted.physical_cells) == 1  # cols 0-1 are covered by the extended merge
    assert len(inserted.cells) == 3  # python-docx-style logical row collection

    created = table.insert_column(1, width=3500)
    assert table.col_count == 4
    assert table.cell(0, 0).span == (3, 3)
    assert table.cell(1, 2).address == (0, 0)
    # Rows covered by the merge do not need a physical cell at the inserted column.
    assert len(created) == 1

    out = tmp_path / "insert-middle-merged.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    t2 = reopened.tables[-1]
    assert (t2.row_count, t2.col_count) == (4, 4)
    assert t2.cell(0, 0).span == (3, 3)
    assert t2.cell(2, 3).text == "old-r1-c2"


def test_delete_row_and_column_relocate_merged_anchor(tmp_path: Path):
    doc = Document.new()
    table = doc.add_table(3, 4, width=40000, height=6000)
    table.cell(0, 0).text = "KEEP"
    table.cell(2, 3).text = "TAIL"
    table.merge_cells(0, 0, 2, 2)

    table.delete_row(0)
    assert table.row_count == 2
    assert table.cell(0, 0).text.startswith("KEEP")
    assert table.cell(0, 0).span == (2, 3)
    assert table.cell(1, 3).text == "TAIL"

    table.delete_column(0)
    assert table.col_count == 3
    assert table.cell(0, 0).text.startswith("KEEP")
    assert table.cell(0, 0).span == (2, 2)
    assert table.cell(1, 2).text == "TAIL"

    out = tmp_path / "delete-merged.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    t2 = reopened.tables[-1]
    assert (t2.row_count, t2.col_count) == (2, 3)
    assert t2.cell(0, 0).span == (2, 2)
    assert t2.cell(0, 0).text.startswith("KEEP")
    assert t2.cell(1, 2).text == "TAIL"


def test_page_total_field_roundtrip(tmp_path: Path):
    doc = Document.new()
    footer = doc.sections[0].footer
    p = footer.add_paragraph("쪽 ")
    footer.add_page_total_field(paragraph=p, position="BOTTOM_CENTER", separator=" / ")

    out = tmp_path / "page-total.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    f2 = reopened.sections[0].footer
    assert "쪽 " in f2.text
    assert " / " in f2.text

    with ZipFile(out) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
        hp = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
        logical = root.find(f".//{hp}secPr/{hp}footer")
        mirror = root.find(f".//{hp}ctrl/{hp}footer")
        assert logical is not None and mirror is not None
        assert etree.tostring(logical, method="c14n") == etree.tostring(mirror, method="c14n")
        assert logical.find(f".//{hp}autoNum[@numType='PAGE']") is not None
        assert logical.find(f".//{hp}autoNum[@numType='TOTAL_PAGE']") is not None
        assert any((t.text or "") == " / " for t in logical.findall(f".//{hp}t"))


def test_numbered_list_continuation_restart_and_start(tmp_path: Path):
    doc = Document.new()
    first = doc.add_list_paragraph("one", kind="number")
    second = doc.add_list_paragraph("two", kind="number")
    restarted = doc.add_list_paragraph("five", kind="number", restart=True, start=5)

    assert first.para_pr_id_ref == second.para_pr_id_ref
    assert restarted.para_pr_id_ref != first.para_pr_id_ref

    first_pp = doc.styles.paragraph_property(first.para_pr_id_ref)
    restart_pp = doc.styles.paragraph_property(restarted.para_pr_id_ref)
    first_head = next(c for c in first_pp.children if local_name(c.tag) == "heading")
    restart_head = next(c for c in restart_pp.children if local_name(c.tag) == "heading")
    assert first_head.get("idRef") != restart_head.get("idRef")

    out = tmp_path / "list-restart.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    rp = next(p for p in reopened.paragraphs if p.text == "five")
    pp = reopened.styles.paragraph_property(rp.para_pr_id_ref)
    head = next(c for c in pp.children if local_name(c.tag) == "heading")
    numbering_id = head.get("idRef")

    with ZipFile(out) as zf:
        header = etree.fromstring(zf.read("Contents/header.xml"))
        hh = "{http://www.hancom.co.kr/hwpml/2011/head}"
        numbering = header.find(f".//{hh}numbering[@id='{numbering_id}']")
        assert numbering is not None
        assert numbering.get("start") == "5"
        assert numbering.find(f"{hh}paraHead").get("start") == "5"


def test_bookmark_and_hyperlink_roundtrip(tmp_path: Path):
    doc = Document.new()
    target = doc.add_paragraph("도착점")
    target.add_bookmark("target-1")
    p = doc.add_paragraph("링크: ")
    link = p.add_hyperlink("#target-1", "문서 안 이동")
    web = p.add_hyperlink("https://example.com/a?b=1#c", " 웹")

    assert target.bookmarks == ["target-1"]
    assert link.url == "#target-1"
    assert link.text == "문서 안 이동"
    assert web.url == "https://example.com/a?b=1#c"
    assert len(p.hyperlinks) == 2
    web.text = " 사이트"

    out = tmp_path / "hyperlinks.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    target2 = next(x for x in reopened.paragraphs if x.text == "도착점")
    p2 = next(x for x in reopened.paragraphs if "문서 안 이동" in x.text)
    assert target2.bookmarks == ["target-1"]
    assert [h.url for h in p2.hyperlinks] == ["#target-1", "https://example.com/a?b=1#c"]
    assert p2.hyperlinks[1].text == " 사이트"

    # Default hyperlink look is copy-on-write blue + blue underline.
    display_run = p2.hyperlinks[0]._display_run
    char_ref = display_run.get("charPrIDRef")
    cp = reopened.styles.char_property(char_ref)
    assert cp is not None and cp.get("textColor") == "#0000FF"
    underline = next(c for c in cp.children if local_name(c.tag) == "underline")
    assert underline.get("type") == "BOTTOM" and underline.get("color") == "#0000FF"

    with ZipFile(out) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
        hp = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
        begins = root.findall(f".//{hp}fieldBegin[@type='HYPERLINK']")
        assert len(begins) == 2
        params = {n.get("name"): (n.text or "") for n in begins[0].find(f"{hp}parameters")}
        assert params["Category"] == "HWPHYPERLINK_TYPE_HWP"
        assert params["Command"].startswith("?target-1")
        web_params = {n.get("name"): (n.text or "") for n in begins[1].find(f"{hp}parameters")}
        assert web_params["Path"] == "https://example.com/a?b=1#c"
        assert web_params["Category"] == "HWPHYPERLINK_TYPE_URL"


def test_document_reference_convenience_api(tmp_path: Path):
    doc = Document.new()
    p = doc.add_paragraph("reference ")
    doc.add_bookmark("here", paragraph=p)
    doc.add_hyperlink("mailto:test@example.com", "mail", paragraph=p)
    out = tmp_path / "refs-convenience.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    p2 = next(x for x in reopened.paragraphs if x.text.startswith("reference"))
    assert "here" in p2.bookmarks
    assert p2.hyperlinks[0].url == "mailto:test@example.com"


def test_v07_python_docx_shaped_heading_page_break_and_run_atoms(tmp_path):
    from pywpdoc._engine import Document
    doc = Document.new()
    h = doc.add_heading("호환 제목", level=2)
    assert h.style is not None and h.style.name in {"개요 2", "Outline 2"}
    p = doc.add_paragraph("A")
    r = p.runs[0]
    r.add_tab().add_break("LINE")
    pb = doc.add_page_break()
    assert pb.page_break is True
    out = tmp_path / "compat_breaks.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    assert any(p.text == "호환 제목" for p in reopened.paragraphs)
    assert any(p.page_break for p in reopened.paragraphs)
    atoms = [n for n in reopened.section_model.iter() if local_name(n.tag) in {"tab", "lineBreak"}]
    assert {local_name(n.tag) for n in atoms} == {"tab", "lineBreak"}


def test_v07_extended_font_copy_on_write(tmp_path):
    from pywpdoc._engine import Document
    doc = Document.new()
    p = doc.add_paragraph("x")
    r = p.runs[0]
    base = r.char_pr_id_ref
    r.font.superscript = True
    r.font.shadow = True
    r.font.highlight_color = "#FFF2CC"
    assert r.char_pr_id_ref != base
    cp = doc.styles.char_property(r.char_pr_id_ref)
    assert any(local_name(n.tag) == "supscript" for n in cp.children)
    assert cp.get("shadeColor") == "#FFF2CC"
    out = tmp_path / "font.hwpx"; doc.save(out)
    rr = Document.open(out).paragraphs[-1].runs[0]
    assert rr.font.superscript is True and rr.font.shadow is True


def test_v07_add_style_live_font_and_paragraph_format(tmp_path):
    from pywpdoc._engine import Document, Pt
    doc = Document.new()
    style = doc.styles.add_style("강조 본문", "PARAGRAPH", clone_from="Body")
    style.font.bold = True
    style.font.size = Pt(13)
    style.paragraph_format.alignment = "CENTER"
    p = doc.add_paragraph("스타일 문단")
    p.style = style
    assert p.style.name == "강조 본문"
    assert p.alignment == "CENTER"
    out=tmp_path/"style.hwpx"; doc.save(out)
    reopened=Document.open(out)
    rs=reopened.styles["강조 본문"]
    assert rs.font.bold is True


def test_v07_table_compatibility_properties_and_bulk_ops(tmp_path):
    from pywpdoc._engine import Document
    doc=Document.new(); t=doc.add_table(2,2)
    t.alignment="CENTER"; t.autofit=False; t.style="Table Grid"
    t.merge_cells(0,0,0,1)
    t.insert_rows(1,2); t.insert_columns(1,2)
    assert t.row_count==4 and t.col_count==4
    t.delete_rows(1,1); t.delete_columns(1,1)
    assert t.row_count==3 and t.col_count==3
    assert t.alignment=="CENTER" and t.autofit is False
    out=tmp_path/"table.hwpx"; doc.save(out)
    reopened=Document.open(out); rt=reopened.tables[0]
    assert rt.row_count==3 and rt.col_count==3 and rt.alignment=="CENTER"


def test_v06_carried_forward_equation_memo_header_fields(tmp_path):
    from pywpdoc._engine import Document
    doc=Document.new(); p=doc.add_paragraph("검토")
    p.add_equation("{a} over {b}")
    memo=p.add_memo("확인 필요", author="검토자")
    header=doc.sections[0].header
    header.add_date_field("2026년 10월 4일")
    footer=doc.sections[0].footer
    footer.add_path_field("sample.hwpx")
    out=tmp_path/"advanced.hwpx"; doc.save(out)
    reopened=Document.open(out)
    names=[local_name(n.tag) for n in reopened.section_model.iter()]
    assert "equation" in names and "script" in names and "memogroup" in names
    fields=[n for n in reopened.section_model.iter() if local_name(n.tag)=="fieldBegin"]
    assert any(n.get("type")=="MEMO" for n in fields)
    secpr=next(n for n in reopened.section_model.iter() if local_name(n.tag)=="secPr")
    story_fields=[n.get("type") for n in secpr.iter() if local_name(n.tag)=="fieldBegin"]
    assert "DATE" in story_fields and "PATH" in story_fields


def test_v06_carried_forward_picture_crop_effects(tmp_path):
    import zipfile
    from pywpdoc._engine import Document
    fixture = Path(__file__).parent / "fixtures" / "original_notice.hwpx"
    with zipfile.ZipFile(fixture) as zf:
        image=zf.read("BinData/image1.png")
    doc=Document.new(); pic=doc.add_picture(image,"png",width=8000,height=6000)
    pic.crop(left=.1, top=.2, right=.1, bottom=.1)
    before=pic.crop_box
    pic.brightness=12; pic.contrast=-8
    pic.resize(width=10000,height=7500)
    after=pic.crop_box
    assert all(abs(a-b)<0.01 for a,b in zip(before,after))
    assert pic.brightness==12 and pic.contrast==-8
    out=tmp_path/"picture.hwpx"; doc.save(out)
    rp=Document.open(out).pictures[0]
    assert rp.brightness==12 and rp.contrast==-8


def test_shared_style_ids_remain_dense_after_cow_save(tmp_path: Path):
    from pywpdoc._engine import Pt
    from pywpdoc._engine.model import local_name
    from pywpdoc._engine.styles import _container

    doc = Document.open(SOURCE)
    p = doc.all_paragraphs[8]
    p.runs[0].bold = True
    p.runs[0].font.size = Pt(13.5)
    p.runs[0].font.color = "#336699"
    p.alignment = "CENTER"
    p.paragraph_format.space_after = Pt(4)
    cell = doc.tables[1].cell(0, 0)
    cell.border.color = "#7030A0"
    cell.fill_color = "#FFF2CC"

    out = tmp_path / "dense-shared-ids.hwpx"
    doc.save(out)
    reopened = Document.open(out)

    specs = [
        ("charProperties", "charPr", 0),
        ("paraProperties", "paraPr", 0),
        ("borderFills", "borderFill", 1),
    ]
    for container_name, child_name, first in specs:
        container = _container(reopened.header_model, container_name)
        ids = [int(node.get("id")) for node in container.children if local_name(node.tag) == child_name]
        assert ids == list(range(first, first + len(ids)))


def test_run_add_tab_uses_mixed_content_inside_text(tmp_path: Path):
    from zipfile import ZipFile
    from lxml import etree

    doc = Document.new()
    p = doc.add_paragraph("before")
    run = p.runs[0]
    run.add_tab()
    p.add_run("after")
    out = tmp_path / "tab-mixed-content.hwpx"
    doc.save(out)

    with ZipFile(out) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
    ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
    assert root.xpath("count(.//hp:t/hp:tab)", namespaces=ns) == 1.0
    assert root.xpath("count(.//hp:run/hp:tab)", namespaces=ns) == 0.0


def test_v08_run_and_paragraph_text_map_tabs_and_breaks(tmp_path: Path):
    from pywpdoc._engine import Document

    doc = Document.new()
    p = doc.add_paragraph("A\tB\nC")
    assert p.text == "A\tB\nC"
    assert p.runs[0].text == "A\tB\nC"

    # Paragraph.text follows python-docx semantics: replace content with one run
    # while preserving paragraph-level formatting.
    p.alignment = "CENTER"
    p.text = "X\tY\nZ"
    assert len(p.runs) == 1
    assert p.text == "X\tY\nZ"
    assert p.alignment == "CENTER"

    out = tmp_path / "mixed-text.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    rp = reopened.paragraphs[-1]
    assert rp.text == "X\tY\nZ"

    with ZipFile(out) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
    ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
    assert root.xpath("count(.//hp:t/hp:tab)", namespaces=ns) == 1.0
    assert root.xpath("count(.//hp:t/hp:lineBreak)", namespaces=ns) == 1.0


def test_v08_insert_paragraph_before_and_style_argument(tmp_path: Path):
    from pywpdoc._engine import Document

    doc = Document.new()
    style = doc.styles.add_style("Notice Body", "PARAGRAPH", clone_from="Body")
    p = doc.add_paragraph("after", style=style)
    before = p.insert_paragraph_before("before", style=style)
    assert before.style is not None and before.style.name == "Notice Body"

    # Also works inside a table-cell subList, not just the section root.
    table = doc.add_table(1, 1)
    cell_p = table.cell(0, 0).paragraphs[0]
    cell_p.text = "cell-after"
    cell_before = cell_p.insert_paragraph_before("cell-before")
    assert table.cell(0, 0).paragraphs[0].text == "cell-before"
    assert table.cell(0, 0).paragraphs[1].text == "cell-after"

    out = tmp_path / "insert-before.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    texts = [x.text for x in reopened.paragraphs]
    assert texts.index("before") < texts.index("after")
    assert reopened.tables[0].cell(0, 0).paragraphs[0].text == "cell-before"


def test_v08_clear_preserves_section_setup(tmp_path: Path):
    from pywpdoc._engine import Document

    doc = Document.new()
    first = doc.sections[0].paragraphs[0]
    assert any(local_name(n.tag) == "secPr" for n in first.element_model.iter())
    first.clear()
    assert any(local_name(n.tag) == "secPr" for n in first.element_model.iter())
    assert first.text == ""

    first.runs[0].clear()
    assert any(local_name(n.tag) == "secPr" for n in first.element_model.iter())

    out = tmp_path / "clear-safe.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    assert any(local_name(n.tag) == "secPr" for n in reopened.sections[0].paragraphs[0].element_model.iter())


def test_v08_tab_stops_python_docx_shaped_api(tmp_path: Path):
    from pywpdoc._engine import Document, Mm, WD_TAB_ALIGNMENT, WD_TAB_LEADER

    doc = Document.new()
    p = doc.add_paragraph("이름\t홍길동")
    tabs = p.paragraph_format.tab_stops
    t1 = tabs.add_tab_stop(Mm(30), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    t2 = tabs.add_tab_stop(Mm(60), WD_TAB_ALIGNMENT.CENTER, WD_TAB_LEADER.DASHES)
    assert len(tabs) == 2
    assert t1.position == Mm(30)
    assert t2.alignment == WD_TAB_ALIGNMENT.CENTER
    assert t2.leader == WD_TAB_LEADER.DASHES

    # Live mutation reauthors/dedupes the referenced tabPr.
    tabs[0].position = Mm(35)
    assert tabs[0].position == Mm(35)
    del tabs[1]
    assert len(tabs) == 1

    out = tmp_path / "tab-stops.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    rp = reopened.paragraphs[-1]
    rtabs = rp.paragraph_format.tab_stops
    assert len(rtabs) == 1
    assert rtabs[0].position == Mm(35)
    assert rtabs[0].alignment == WD_TAB_ALIGNMENT.RIGHT

    with ZipFile(out) as zf:
        header = etree.fromstring(zf.read("Contents/header.xml"))
    ns = {
        "hh": "http://www.hancom.co.kr/hwpml/2011/head",
        "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    }
    # Native Hancom layout: each stop is switch/case(default), case position is HWPUNIT.
    cases = header.xpath(".//hh:tabPr/hp:switch/hp:case/hh:tabItem", namespaces=ns)
    assert any(int(item.get("pos")) == int(Mm(35)) for item in cases)


def test_v08_even_odd_header_footer_facade(tmp_path: Path):
    from pywpdoc._engine import Document

    doc = Document.new()
    section = doc.sections[0]
    section.header.text = "공통 머리말"
    section.even_page_header.text = "짝수 머리말"
    section.odd_page_footer.text = "홀수 꼬리말"
    assert section.even_page_header.apply_page_type == "EVEN"
    assert section.odd_page_footer.apply_page_type == "ODD"

    try:
        _ = section.first_page_header
    except NotImplementedError as exc:
        assert "distinct first-page" in str(exc)
    else:
        raise AssertionError("first_page_header must fail closed until HWPX semantics are verified")

    out = tmp_path / "even-odd-stories.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    rs = reopened.sections[0]
    assert rs.header.text == "공통 머리말"
    assert rs.even_page_header.text == "짝수 머리말"
    assert rs.odd_page_footer.text == "홀수 꼬리말"


def test_v08_document_iter_inner_content_collapses_table_wrappers(tmp_path: Path):
    from pywpdoc._engine import Document, Paragraph, Table

    doc = Document.new()
    doc.add_paragraph("P1")
    table = doc.add_table(1, 1, style="Table Grid")
    table.cell(0, 0).text = "T"
    doc.add_paragraph("P2")

    content = list(doc.iter_inner_content())
    assert [type(x) for x in content] == [Paragraph, Table, Paragraph]
    assert content[0].text == "P1"
    assert content[1].cell(0, 0).text == "T"
    assert content[2].text == "P2"

    out = tmp_path / "inner-content.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    assert [type(x).__name__ for x in reopened.iter_inner_content()] == ["Paragraph", "Table", "Paragraph"]


def test_v08_paragraph_iter_inner_content_yields_hyperlink_once():
    from pywpdoc._engine import Document, Run, Hyperlink

    doc = Document.new()
    p = doc.add_paragraph("before ")
    p.add_hyperlink("https://example.com", "link")
    p.add_run(" after")
    content = list(p.iter_inner_content())
    assert [type(x) for x in content] == [Run, Hyperlink, Run]
    assert p.text == "before link after"


def test_v08_save_validation_is_atomic(tmp_path: Path):
    from pywpdoc._engine import Document, validate_hwpx_file

    target = tmp_path / "atomic.hwpx"
    target.write_bytes(b"ORIGINAL")
    doc = Document.new()
    p = doc.add_paragraph("bad ref")
    p.runs[0].char_pr_id_ref = "99999"

    try:
        doc.save(target)
    except ValueError as exc:
        assert "validation failed" in str(exc).lower()
    else:
        raise AssertionError("save must reject dangling shared-style references")
    assert target.read_bytes() == b"ORIGINAL"

    good = Document.new()
    good.add_paragraph("valid")
    good.save(target)
    report = validate_hwpx_file(target)
    assert report.ok, report.issues
    assert set(report.checks) >= {"zip-integrity", "mimetype", "public-reopen"}


def test_v08_units_and_break_enum(tmp_path: Path):
    from pywpdoc._engine import Document, Cm, Inches, Mm, WD_BREAK

    assert Cm(2.54) == Inches(1)
    assert round(Inches(1).mm, 5) == 25.4
    assert abs(Mm(10).cm - 1.0) < 0.001

    doc = Document.new()
    p = doc.add_paragraph("A")
    p.runs[0].add_break(WD_BREAK.LINE)
    assert p.text == "A\n"
    p.runs[0].add_break(WD_BREAK.PAGE)
    assert p.page_break is True
    out = tmp_path / "enum-breaks.hwpx"
    doc.save(out)
    assert Document.open(out).paragraphs[-1].page_break is True


def test_v09_table_columns_and_merged_width_roundtrip(tmp_path: Path):
    from pywpdoc._engine import Document, Mm

    doc = Document.new()
    table = doc.add_table(3, 3, width=int(Mm(90)))
    table.cell(0, 0).text = "merged"
    table.merge_cells(0, 0, 0, 1)
    before_total = int(table._size_node().get("width") or 0)
    old = table.columns[1].width
    table.columns[1].width = Mm(40)
    delta = int(Mm(40)) - int(old)

    assert len(table.columns) == 3
    assert table.columns[1].width == Mm(40)
    assert int(table._size_node().get("width") or 0) == before_total + delta
    # The merged anchor spans columns 0 and 1, so changing column 1 must
    # change that physical cell's combined width by the same delta.
    assert table.cell(0, 0).width == int(table.columns[0].width) + int(table.columns[1].width)
    assert len(table.columns[2].cells) == 3

    out = tmp_path / "columns-width.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    rt = reopened.tables[0]
    assert rt.columns[1].width == Mm(40)
    assert rt.cell(0, 0).text == "merged"
    assert rt.cell(0, 0).span == (1, 2)


def test_v09_cell_vertical_alignment_python_docx_facade(tmp_path: Path):
    from pywpdoc._engine import Document, WD_CELL_VERTICAL_ALIGNMENT

    doc = Document.new()
    table = doc.add_table(1, 3)
    values = [
        WD_CELL_VERTICAL_ALIGNMENT.TOP,
        WD_CELL_VERTICAL_ALIGNMENT.CENTER,
        WD_CELL_VERTICAL_ALIGNMENT.BOTTOM,
    ]
    for i, value in enumerate(values):
        table.cell(0, i).vertical_alignment = value
        table.cell(0, i).text = value.name
        assert table.cell(0, i).vertical_alignment == value

    out = tmp_path / "cell-vertical-align.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    assert [reopened.tables[0].cell(0, i).vertical_alignment for i in range(3)] == values


def test_v09_section_python_docx_shaped_page_facade(tmp_path: Path):
    from pywpdoc._engine import Document, Mm, WD_ORIENT

    doc = Document.new()
    section = doc.sections[0]
    section.left_margin = Mm(12)
    section.right_margin = Mm(14)
    section.top_margin = Mm(16)
    section.bottom_margin = Mm(18)
    section.header_distance = Mm(8)
    section.footer_distance = Mm(9)
    section.orientation = WD_ORIENT.LANDSCAPE

    assert section.left_margin == Mm(12)
    assert section.footer_distance == Mm(9)
    assert section.orientation == WD_ORIENT.LANDSCAPE
    assert section.page_setup.landscape == "NARROWLY"

    out = tmp_path / "section-facade.hwpx"
    doc.save(out)
    rs = Document.open(out).sections[0]
    assert rs.orientation == WD_ORIENT.LANDSCAPE
    assert rs.left_margin == Mm(12)
    assert rs.right_margin == Mm(14)


def test_v09_core_properties_roundtrip(tmp_path: Path):
    from datetime import datetime
    from pywpdoc._engine import Document

    doc = Document.new()
    props = doc.core_properties
    props.title = "HWPX용 python-docx"
    props.author = "OpenAI"
    props.subject = "v0.9 metadata"
    props.comments = "core properties facade"
    props.keywords = "hwpx,python-docx"
    props.last_modified_by = "tester"
    props.language = "ko"
    props.created = datetime(2026, 10, 4, 12, 30, 0)
    props.modified = datetime(2026, 10, 4, 21, 0, 0)

    out = tmp_path / "core-properties.hwpx"
    doc.save(out)
    rp = Document.open(out).core_properties
    assert rp.title == "HWPX용 python-docx"
    assert rp.author == "OpenAI"
    assert rp.subject == "v0.9 metadata"
    assert rp.comments == "core properties facade"
    assert rp.keywords == "hwpx,python-docx"
    assert rp.last_modified_by == "tester"
    assert rp.created == datetime(2026, 10, 4, 12, 30, 0)
    assert rp.modified == datetime(2026, 10, 4, 21, 0, 0)


def test_v09_settings_caret_typed_roundtrip(tmp_path: Path):
    from pywpdoc._engine import Document

    doc = Document.new()
    caret = doc.settings.caret_position
    caret.list_id_ref = 2
    caret.para_id_ref = 12345
    caret.pos = 7
    out = tmp_path / "settings-caret.hwpx"
    doc.save(out)

    reopened = Document.open(out)
    rc = reopened.settings.caret_position
    assert (rc.list_id_ref, rc.para_id_ref, rc.pos) == (2, 12345, 7)


def test_v09_style_delete_compacts_ids_and_repoints_paragraphs(tmp_path: Path):
    from pywpdoc._engine import Document

    doc = Document.new()
    s1 = doc.styles.add_style("Delete Me", "PARAGRAPH", clone_from="Body")
    s2 = doc.styles.add_style("Keep Me", "PARAGRAPH", clone_from="Body")
    p1 = doc.add_paragraph("deleted-style", style=s1)
    p2 = doc.add_paragraph("kept-style", style=s2)
    old_s2_id = s2.id
    s1.delete()

    assert doc.styles.get("Delete Me") is None
    assert p1.style_id_ref == "0"
    kept = doc.styles["Keep Me"]
    assert int(kept.id) == int(old_s2_id) - 1
    assert p2.style_id_ref == kept.id

    out = tmp_path / "style-delete.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    assert reopened.styles.get("Delete Me") is None
    assert reopened.styles.get("Keep Me") is not None
    assert next(p for p in reopened.paragraphs if p.text == "kept-style").style.name == "Keep Me"


def test_v010_styles_iter_style_type_and_default_contract():
    from pywpdoc._engine import Document, Style, WD_STYLE_TYPE

    doc = Document.new()
    styles = doc.styles
    assert all(isinstance(style, Style) for style in styles)
    assert "Normal" in styles
    assert styles.default(WD_STYLE_TYPE.PARAGRAPH).id == "0"
    assert styles.default(WD_STYLE_TYPE.CHARACTER) is None

    paragraph_style = styles.add_style("V010 Paragraph", WD_STYLE_TYPE.PARAGRAPH, clone_from="Body")
    character_style = styles.add_style("V010 Character", WD_STYLE_TYPE.CHARACTER, clone_from="Page Number")
    assert paragraph_style.style_type == WD_STYLE_TYPE.PARAGRAPH
    assert character_style.style_type == WD_STYLE_TYPE.CHARACTER

    try:
        styles.add_style("Unsupported Table Style", WD_STYLE_TYPE.TABLE)
    except NotImplementedError:
        pass
    else:
        raise AssertionError("unverified HWPX table-style definitions must fail closed")


def test_v010_next_paragraph_style_roundtrip(tmp_path: Path):
    from pywpdoc._engine import Document, WD_STYLE_TYPE

    doc = Document.new()
    a = doc.styles.add_style("Question", WD_STYLE_TYPE.PARAGRAPH, clone_from="Body")
    b = doc.styles.add_style("Answer", WD_STYLE_TYPE.PARAGRAPH, clone_from="Body")
    a.next_paragraph_style = b
    assert a.next_paragraph_style.name == "Answer"

    out = tmp_path / "next-style.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    assert reopened.styles["Question"].next_paragraph_style.name == "Answer"

    reopened.styles["Question"].next_paragraph_style = None
    assert reopened.styles["Question"].next_paragraph_style.name == "Question"


def test_v010_run_character_style_facade(tmp_path: Path):
    from pywpdoc._engine import Document, WD_STYLE_TYPE

    doc = Document.new()
    style = doc.styles.add_style("Inline Emphasis", WD_STYLE_TYPE.CHARACTER, clone_from="Page Number")
    style.font.bold = True
    style.font.italic = True
    p = doc.add_paragraph("A")
    run = p.add_run("B")
    run.style = style
    assert run.style is not None and run.style.name == "Inline Emphasis"
    assert run.bold is True and run.italic is True

    out = tmp_path / "run-style.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    rr = reopened.paragraphs[-1].runs[-1]
    assert rr.style is not None and rr.style.name == "Inline Emphasis"


def test_v010_insert_before_section_carrier_keeps_section_setup_first(tmp_path: Path):
    from pywpdoc._engine import Document

    doc = Document.new()
    first = doc.sections[0].paragraphs[0]
    assert any(local_name(n.tag) == "secPr" for n in first.element_model.iter())
    inserted = first.insert_paragraph_before("앞 문단")
    section_paragraphs = doc.sections[0].paragraphs
    assert section_paragraphs[0].element_model is inserted.element_model
    assert any(local_name(n.tag) == "secPr" for n in inserted.element_model.iter())
    assert not any(local_name(n.tag) == "secPr" for n in first.element_model.iter())

    out = tmp_path / "insert-before-section-carrier.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    assert len(reopened.sections) == 1
    assert any(local_name(n.tag) == "secPr" for n in reopened.sections[0].paragraphs[0].element_model.iter())
    assert reopened.sections[0].paragraphs[0].text == "앞 문단"


def test_v010_row_height_updates_vertical_merge_and_roundtrips(tmp_path: Path):
    from pywpdoc._engine import Document, Mm

    doc = Document.new()
    table = doc.add_table(3, 2, width=int(Mm(80)), height=int(Mm(30)))
    table.cell(0, 0).text = "vertical merge"
    table.merge_cells(0, 0, 1, 0)
    before_total = int(table._size_node().get("height") or 0)
    old = table.rows[1].height
    merged_before = table.cell(0, 0).height
    table.rows[1].height = Mm(15)
    delta = int(Mm(15)) - int(old)
    assert table.rows[1].height == Mm(15)
    assert table.cell(0, 0).height == merged_before + delta
    assert int(table._size_node().get("height") or 0) == before_total + delta
    assert table.rows[0].table.element_model is table.element_model

    out = tmp_path / "row-height.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    assert reopened.tables[0].rows[1].height == Mm(15)


def test_v010_cell_merge_nested_table_and_text_replacement(tmp_path: Path):
    from pywpdoc._engine import Document, Paragraph, Table

    doc = Document.new()
    table = doc.add_table(2, 2, style="Table Grid")
    table.cell(0, 0).text = "A"
    merged = table.cell(0, 0).merge(table.cell(1, 1))
    assert merged.span == (2, 2)
    assert merged.text == "A"

    outer = doc.add_table(1, 1, style="Table Grid")
    cell = outer.cell(0, 0)
    nested = cell.add_table(2, 2, style="Table Grid")
    nested.cell(0, 0).text = "nested"
    assert len(cell.tables) == 1
    assert len(doc.tables) == 2
    assert len(doc.all_tables) == 3
    blocks = list(cell.iter_inner_content())
    assert any(isinstance(x, Table) for x in blocks)
    assert all(isinstance(x, (Paragraph, Table)) for x in blocks)

    cell.text = "replacement"
    assert cell.text == "replacement"
    assert cell.tables == []
    assert len(cell.paragraphs) == 1

    out = tmp_path / "cell-nested-table.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    assert reopened.tables[0].cell(0, 0).span == (2, 2)
    assert reopened.tables[1].cell(0, 0).text == "replacement"


def test_v010_header_footer_style_argument_and_page_break_alias(tmp_path: Path):
    from pywpdoc._engine import Document, WD_STYLE_TYPE

    doc = Document.new()
    style = doc.styles.add_style("Header Custom", WD_STYLE_TYPE.PARAGRAPH, clone_from="Header")
    header = doc.sections[0].header
    header.clear_content()
    p = header.add_paragraph("머리말", style=style)
    assert p.style is not None and p.style.name == "Header Custom"

    body = doc.add_paragraph("본문")
    assert body.contains_page_break is False
    body.page_break = True
    assert body.contains_page_break is True

    out = tmp_path / "header-style.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    hp = reopened.sections[0].header.paragraphs[-1]
    assert hp.style is not None and hp.style.name == "Header Custom"
    assert reopened.paragraphs[-1].contains_page_break is True


def test_v010_header_footer_block_container_table_roundtrip(tmp_path: Path):
    from pywpdoc._engine import Document, Paragraph, Table, Mm

    doc = Document.new()
    header = doc.sections[0].header
    header.clear_content()
    header.add_paragraph("앞머리")
    table = header.add_table(1, 2, style="Table Grid", width=int(Mm(80)))
    table.cell(0, 0).text = "L"
    table.cell(0, 1).text = "R"
    header.add_paragraph("뒷머리")

    assert len(header.tables) == 1
    assert doc.tables == []
    assert len(doc.all_tables) == 1
    blocks = list(header.iter_inner_content())
    assert [type(x) for x in blocks] == [Paragraph, Paragraph, Table, Paragraph]
    assert blocks[0].text == ""

    out = tmp_path / "header-table.hwpx"
    doc.save(out)
    rh = Document.open(out).sections[0].header
    assert [type(x).__name__ for x in rh.iter_inner_content()] == ["Paragraph", "Paragraph", "Table", "Paragraph"]
    assert rh.tables[0].cell(0, 1).text == "R"

    with ZipFile(out) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
    ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
    headers = root.xpath(".//hp:header[@applyPageType='BOTH']", namespaces=ns)
    assert len(headers) == 2  # logical story + Hancom-read control mirror
    assert etree.tostring(headers[0], method="c14n") == etree.tostring(headers[1], method="c14n")


def test_v011_paragraph_replace_spans_runs_and_preserves_first_run_format(tmp_path: Path):
    from pywpdoc._engine import Document

    doc = Document.new()
    p = doc.add_paragraph()
    r1 = p.add_run("202")
    r1.bold = True
    r2 = p.add_run("6학년도")
    r2.italic = True
    assert p.text == "2026학년도"

    changed = p.replace("2026", "2027")
    assert changed == 1
    assert p.text == "2027학년도"
    assert r1.bold is True
    assert r2.italic is True
    assert r1.text == "2027"
    assert r2.text == "학년도"

    out = tmp_path / "replace-runs.hwpx"
    doc.save(out)
    rp = Document.open(out).paragraphs[-1]
    assert rp.text == "2027학년도"
    visible = [run for run in rp.runs if run.text]
    assert visible[0].bold is True
    assert visible[1].italic is True


def test_v011_paragraph_replace_can_cross_hyperlink_boundary(tmp_path: Path):
    from pywpdoc._engine import Document

    doc = Document.new()
    p = doc.add_paragraph("Hello ")
    link = p.add_hyperlink("https://example.com", "world")
    p.add_run("!")
    assert p.text == "Hello world!"

    assert p.replace("ello world", "i there") == 1
    assert p.text == "Hi there!"
    # The replacement inherits the first matched segment; the hyperlink field
    # survives but its fully-consumed visible text becomes empty.
    assert len(p.hyperlinks) == 1
    assert p.hyperlinks[0].url == "https://example.com"
    assert p.hyperlinks[0].text == ""

    out = tmp_path / "replace-hyperlink.hwpx"
    doc.save(out)
    rp = Document.open(out).paragraphs[-1]
    assert rp.text == "Hi there!"
    assert len(rp.hyperlinks) == 1


def test_v011_document_replace_everywhere_dedupes_story_mirrors_and_skips_memo(tmp_path: Path):
    from pywpdoc._engine import Document

    doc = Document.new()
    body = doc.add_paragraph("YEAR")
    table = doc.add_table(1, 1, style="Table Grid")
    table.cell(0, 0).text = "YEAR"
    doc.sections[0].header.text = "YEAR"
    memo_anchor = doc.add_paragraph("anchor")
    memo_anchor.add_memo("YEAR memo", author="tester")

    assert doc.replace("YEAR", "2027", everywhere=True) == 3
    assert body.text == "2027"
    assert table.cell(0, 0).text == "2027"
    assert doc.sections[0].header.text == "2027"

    out = tmp_path / "replace-everywhere.hwpx"
    doc.save(out)
    reopened = Document.open(out)
    assert reopened.sections[0].header.text == "2027"
    assert reopened.tables[0].cell(0, 0).text == "2027"
    memo_texts = [
        "".join((n.text or "") for n in memo.iter() if local_name(n.tag) == "t")
        for section in reopened.section_models
        for memo in section.iter()
        if local_name(memo.tag) == "memo"
    ]
    assert any("YEAR memo" in text for text in memo_texts)


def test_v011_document_replace_body_only_leaves_table_and_header_untouched():
    from pywpdoc._engine import Document

    doc = Document.new()
    doc.add_paragraph("TOKEN")
    table = doc.add_table(1, 1)
    table.cell(0, 0).text = "TOKEN"
    doc.sections[0].header.text = "TOKEN"
    assert doc.replace("TOKEN", "BODY", everywhere=False) == 1
    assert doc.paragraphs[-1].text == "BODY"
    assert table.cell(0, 0).text == "TOKEN"
    assert doc.sections[0].header.text == "TOKEN"


def test_v011_text_mutation_drops_stale_linesegarray():
    from pywpdoc._engine import Document
    from pywpdoc._engine.model import ElementModel, HP

    doc = Document.new()
    p = doc.add_paragraph("old")
    p.element_model.children.append(ElementModel(HP + "linesegarray"))
    assert any(local_name(c.tag) == "linesegarray" for c in p.element_model.children)
    p.runs[0].text = "new"
    assert not any(local_name(c.tag) == "linesegarray" for c in p.element_model.children)


def test_v011_row_cells_are_logical_and_physical_cells_are_explicit():
    from pywpdoc._engine import Document

    doc = Document.new()
    table = doc.add_table(2, 3)
    table.cell(0, 0).text = "merged"
    table.merge_cells(0, 0, 1, 1)
    assert len(table.rows[0].cells) == 3
    assert len(table.rows[1].cells) == 3
    assert table.rows[0].cells[0].element_model is table.rows[0].cells[1].element_model
    assert table.rows[1].cells[0].element_model is table.rows[0].cells[0].element_model
    assert len(table.rows[0].physical_cells) == 2
    assert len(table.rows[1].physical_cells) == 1


def test_v011_validation_error_is_structured_and_backwards_valueerror(tmp_path: Path):
    from pywpdoc._engine import Document, HwpxValidationError

    doc = Document.new()
    p = doc.add_paragraph("bad")
    p.runs[0].char_pr_id_ref = "99999"
    try:
        doc.save(tmp_path / "bad.hwpx")
    except HwpxValidationError as exc:
        assert isinstance(exc, ValueError)
        assert exc.code == "validation-failed"
        assert exc.report is not None
        assert any(issue.code == "charpr-ref-missing" for issue in exc.report.errors)
        assert exc.to_dict()["code"] == "validation-failed"
    else:
        raise AssertionError("expected structured validation error")


def test_v012_targeted_body_edit_preserves_unrelated_parts_byte_exact(tmp_path: Path):
    """Editing body text must not churn untouched package-part bytes."""
    from pywpdoc._engine import Document

    source = SOURCE
    doc = Document.open(source)
    paragraph = next(p for p in doc.paragraphs if p.text.strip())
    paragraph.text = paragraph.text + " [v0.12]"
    out = tmp_path / "targeted-body-edit.hwpx"
    doc.save(out)

    with ZipFile(source) as before, ZipFile(out) as after:
        assert before.namelist() == after.namelist()
        for name in before.namelist():
            if name == "Contents/section0.xml":
                assert before.read(name) != after.read(name)
            else:
                assert before.read(name) == after.read(name), name


def test_v012_targeted_metadata_edit_preserves_all_other_parts_byte_exact(tmp_path: Path):
    from pywpdoc._engine import Document

    source = SOURCE
    doc = Document.open(source)
    doc.core_properties.title = "metadata only"
    out = tmp_path / "targeted-metadata-edit.hwpx"
    doc.save(out)

    with ZipFile(source) as before, ZipFile(out) as after:
        assert before.namelist() == after.namelist()
        for name in before.namelist():
            if name == "Contents/content.hpf":
                assert before.read(name) != after.read(name)
            else:
                assert before.read(name) == after.read(name), name


def test_v012_accessing_settings_without_mutation_does_not_churn_settings_bytes(tmp_path: Path):
    from pywpdoc._engine import Document

    source = SOURCE
    doc = Document.open(source)
    _ = doc.settings.caret_position.pos
    out = tmp_path / "settings-read-only.hwpx"
    doc.save(out)
    with ZipFile(source) as before, ZipFile(out) as after:
        assert before.read("settings.xml") == after.read("settings.xml")


def test_v012_paragraph_style_rebases_direct_run_formatting(tmp_path: Path):
    from pywpdoc._engine import Document, WD_STYLE_TYPE, Pt

    doc = Document.new()
    style_a = doc.styles.add_style("Stable A", WD_STYLE_TYPE.PARAGRAPH, clone_from="Body")
    style_a.font.italic = True
    style_b = doc.styles.add_style("Stable B", WD_STYLE_TYPE.PARAGRAPH, clone_from="Body")
    style_b.font.size = Pt(15)

    p = doc.add_paragraph("base", style=style_a)
    direct = p.add_run(" direct")
    direct.bold = True
    old_direct_ref = direct.char_pr_id_ref

    p.style = style_b
    assert p.style.name == "Stable B"
    # direct bold survives, while the new paragraph style's size is rebased in
    # to the flat HWPX charPr record.
    assert direct.bold is True
    assert direct.font.size is not None
    assert abs(direct.font.size.pt - 15.0) < 0.02
    assert direct.char_pr_id_ref != old_direct_ref

    p.style = None
    assert p.style is not None and p.style.id == "0"
    assert direct.bold is True

    out = tmp_path / "style-rebase.hwpx"
    doc.save(out)
    rp = Document.open(out).paragraphs[-1]
    assert rp.style is not None and rp.style.id == "0"
    assert rp.runs[-1].bold is True


def test_v012_run_clear_drops_stale_layout_cache():
    from pywpdoc._engine import Document
    from pywpdoc._engine.model import ElementModel, HP

    doc = Document.new()
    p = doc.add_paragraph("cached")
    p.element_model.children.append(ElementModel(HP + "linesegarray"))
    p.runs[-1].clear()
    assert p.text == ""
    assert not any(local_name(child.tag) == "linesegarray" for child in p.element_model.children)


def test_v012_structured_error_and_validation_report_serialization(tmp_path: Path):
    from pywpdoc._engine import Document, HwpxValueError, HwpxValidationError

    doc = Document.new()
    p = doc.add_paragraph("x")
    try:
        p.replace("", "y")
    except HwpxValueError as exc:
        assert isinstance(exc, ValueError)
        assert exc.code == "text-search-empty"
        assert exc.to_dict()["code"] == "text-search-empty"
    else:
        raise AssertionError("expected HwpxValueError")

    p.runs[0].char_pr_id_ref = "999999"
    try:
        doc.save(tmp_path / "invalid.hwpx")
    except HwpxValidationError as exc:
        payload = exc.to_dict()
        assert payload["code"] == "validation-failed"
        assert payload["report"]["ok"] is False
        assert any(issue["code"] == "charpr-ref-missing" for issue in payload["report"]["issues"])
    else:
        raise AssertionError("expected HwpxValidationError")


def test_v012_noop_open_save_preserves_all_package_payloads_byte_exact(tmp_path: Path):
    from pywpdoc._engine import Document

    out = tmp_path / "noop-save.hwpx"
    Document.open(SOURCE).save(out)
    with ZipFile(SOURCE) as before, ZipFile(out) as after:
        assert before.namelist() == after.namelist()
        for name in before.namelist():
            assert before.read(name) == after.read(name), name
            assert before.getinfo(name).compress_type == after.getinfo(name).compress_type
