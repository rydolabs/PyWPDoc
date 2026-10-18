from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest
from lxml import etree

from pywpdoc import Document


FIXTURES = Path(__file__).parent / "fixtures"
DATA = {
    "customer": {"name": "홍길동"},
    "items": [
        {"name": "A", "qty": 2},
        {"name": "B", "qty": 3},
    ],
    "show_note": True,
    "note": "확인",
}


@pytest.mark.parametrize("suffix", ["hwpx", "docx"])
def test_real_authoring_find_sees_tags_and_plain_text_in_all_table_cells(suffix: str):
    doc = Document.open(FIXTURES / f"real_authoring_template_sections.{suffix}")

    assert len(doc.find("{{customer.name}}")) == 1
    assert len(doc.find("{{#items}}")) == 1
    assert len(doc.find("{{qty}}")) == 1
    assert len(doc.find("비고")) == 1
    assert len(doc.find("{{#show_note}}")) == 1
    assert len(doc.find("{{note}}")) == 1


@pytest.mark.parametrize("suffix", ["hwpx", "docx"])
def test_real_authoring_replace_reaches_manual_table_cell_and_survives_reopen(
    suffix: str, tmp_path: Path,
):
    src = FIXTURES / f"real_authoring_template_sections.{suffix}"
    out = tmp_path / f"manual-replace.{suffix}"

    doc = Document.open(src)
    assert doc.replace_text("{{note}}", "확인") == 1
    assert doc.tables[0].cell(1, 0).text == "비고"
    assert doc.tables[0].cell(1, 1).text == "{{#show_note}}확인{{/show_note}}"
    doc.save(out)

    reopened = Document.open(out)
    assert reopened.tables[0].cell(1, 0).text == "비고"
    assert reopened.tables[0].cell(1, 1).text == "{{#show_note}}확인{{/show_note}}"
    assert len(reopened.find("{{note}}")) == 0


@pytest.mark.parametrize("suffix", ["hwpx", "docx"])
def test_real_authoring_template_renders_all_manual_tags_and_survives_reopen(
    suffix: str, tmp_path: Path,
):
    src = FIXTURES / f"real_authoring_template_sections.{suffix}"
    out = tmp_path / f"manual-rendered.{suffix}"

    doc = Document.open(src)
    assert doc.render_template(DATA, sections=True) == 9
    assert len(doc.find("{{")) == 0
    assert doc.tables[0].cell(1, 0).text == "비고"
    assert doc.tables[0].cell(1, 1).text == "확인"
    doc.save(out)

    reopened = Document.open(out)
    assert len(reopened.find("{{")) == 0
    assert len(reopened.find("고객: 홍길동")) == 1
    assert len(reopened.find("[A=2] [B=3]")) == 1
    assert reopened.tables[0].cell(0, 0).text == "항목"
    assert reopened.tables[0].cell(0, 1).text == "값"
    assert reopened.tables[0].cell(1, 0).text == "비고"
    assert reopened.tables[0].cell(1, 1).text == "확인"


def test_real_hancom_fixture_reuses_paragraph_ids_but_cells_remain_distinct():
    src = FIXTURES / "real_authoring_template_sections.hwpx"
    with ZipFile(src) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))

    ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
    zero_id_paragraphs = root.xpath('.//hp:p[@id="0"]', namespaces=ns)
    assert len(zero_id_paragraphs) >= 5

    doc = Document.open(src)
    table = doc.tables[0]
    assert table.cell(0, 0).text == "항목"
    assert table.cell(0, 1).text == "값"
    assert table.cell(1, 0).text == "비고"
    assert table.cell(1, 1).text == "{{#show_note}}{{note}}{{/show_note}}"
    assert len(doc.find("{{note}}")) == 1
