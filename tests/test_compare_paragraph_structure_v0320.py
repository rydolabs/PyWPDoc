"""v0.32 top-level body paragraph insertion/deletion tracked comparison."""
from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest
from lxml import etree

from pywpdoc import Document, DocumentUnsupportedError
from pywpdoc.features.compare import build_revision_plan

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"


def _make(fmt: str, texts: list[str]) -> Document:
    doc = Document.new(fmt)
    for text in texts:
        doc.add_paragraph(text)
    return doc


def _doc_blocks(doc: Document) -> list[str]:
    result: list[str] = []
    for block in doc.iter_inner_content():
        if "paragraph" in type(block).__name__.lower():
            result.append(block.text)
        else:
            result.append("<TABLE>")
    return result


def _docx_para_text(paragraph: etree._Element, *, accepted: bool) -> str:
    ns = {"w": W}
    parts: list[str] = []
    for child in paragraph:
        name = etree.QName(child).localname
        if name == "r":
            parts.extend(t.text or "" for t in child.xpath("./w:t", namespaces=ns))
        elif name == "ins" and accepted:
            parts.extend(t.text or "" for t in child.xpath(".//w:t", namespaces=ns))
        elif name == "del" and not accepted:
            parts.extend(t.text or "" for t in child.xpath(".//w:delText", namespaces=ns))
    return "".join(parts)


def _docx_block_projection(path: Path, *, accepted: bool) -> list[str]:
    with ZipFile(path) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
    ns = {"w": W}
    result: list[str] = []
    body = root.find(f"{{{W}}}body")
    assert body is not None
    for child in body:
        name = etree.QName(child).localname
        if name == "tbl":
            result.append("<TABLE>")
            continue
        if name != "p":
            continue
        inserted_mark = bool(child.xpath("./w:pPr/w:rPr/w:ins", namespaces=ns))
        deleted_mark = bool(child.xpath("./w:pPr/w:rPr/w:del", namespaces=ns))
        if accepted and deleted_mark:
            continue
        if not accepted and inserted_mark:
            continue
        result.append(_docx_para_text(child, accepted=accepted))
    return result


def _hwpx_t_projection(t: etree._Element, *, accepted: bool) -> str:
    parts: list[str] = []
    state = "plain"
    if t.text:
        parts.append(t.text)
    for child in t:
        name = etree.QName(child).localname
        if name == "insertBegin":
            state = "insert"
        elif name == "deleteBegin":
            state = "delete"
        elif name in {"insertEnd", "deleteEnd"}:
            state = "plain"
        if child.tail:
            keep = (
                state == "plain"
                or (state == "insert" and accepted)
                or (state == "delete" and not accepted)
            )
            if keep:
                parts.append(child.tail)
    return "".join(parts)


def _hwpx_block_projection(path: Path, *, accepted: bool) -> list[str]:
    with ZipFile(path) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
    ns = {"hp": HP}
    result: list[str] = []
    for paragraph in root.xpath("./hp:p", namespaces=ns):
        has_table = bool(paragraph.xpath("./hp:run/hp:tbl", namespaces=ns))
        has_secpr = bool(paragraph.xpath("./hp:run/hp:secPr", namespaces=ns))
        inserted_mark = bool(paragraph.xpath(".//hp:insertEnd[@paraend='1']", namespaces=ns))
        deleted_mark = bool(paragraph.xpath(".//hp:deleteEnd[@paraend='1']", namespaces=ns))
        if accepted and deleted_mark:
            continue
        if not accepted and inserted_mark:
            continue
        text = "".join(
            _hwpx_t_projection(t, accepted=accepted)
            for t in paragraph.xpath("./hp:run/hp:t", namespaces=ns)
        )
        if has_table and not text:
            result.append("<TABLE>")
        elif has_secpr and not text and not inserted_mark and not deleted_mark:
            # Hidden HWPX section carrier; Document.iter_inner_content hides it.
            continue
        else:
            result.append(text)
    return result


def _projection(path: Path, fmt: str, *, accepted: bool) -> list[str]:
    return (
        _docx_block_projection(path, accepted=accepted)
        if fmt == "docx"
        else _hwpx_block_projection(path, accepted=accepted)
    )


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_tracked_paragraph_insert_accept_reject_invariant(fmt: str, tmp_path: Path):
    old = _make(fmt, ["A", "B", "C"])
    new = _make(fmt, ["A", "X", "B", "C"])
    old_before = _doc_blocks(old)
    new_before = _doc_blocks(new)

    out = tmp_path / f"paragraph-insert.{fmt}"
    old.compare(new, author="Para QA", date="2026-10-08T06:00:00Z", everywhere=False).save(out)

    assert _projection(out, fmt, accepted=True) == new_before
    assert _projection(out, fmt, accepted=False) == old_before
    assert _doc_blocks(old) == old_before
    assert _doc_blocks(new) == new_before
    assert Document.open(out).format == fmt


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_tracked_paragraph_delete_accept_reject_invariant(fmt: str, tmp_path: Path):
    old = _make(fmt, ["A", "B", "C"])
    new = _make(fmt, ["A", "C"])
    out = tmp_path / f"paragraph-delete.{fmt}"

    old.compare(new, author="Para QA", date="2026-10-08T06:00:00Z", everywhere=False).save(out)

    assert _projection(out, fmt, accepted=True) == _doc_blocks(new)
    assert _projection(out, fmt, accepted=False) == _doc_blocks(old)


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_multiple_adjacent_paragraph_insert_delete_preserve_order(fmt: str, tmp_path: Path):
    old = _make(fmt, ["A", "B", "C", "D"])
    new = _make(fmt, ["A", "X", "Y", "D"])
    out = tmp_path / f"paragraph-multi.{fmt}"

    old.compare(new, author="QA", date="2026-10-08T06:00:00Z", everywhere=False).save(out)

    assert _projection(out, fmt, accepted=True) == ["A", "X", "Y", "D"]
    assert _projection(out, fmt, accepted=False) == ["A", "B", "C", "D"]


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_paragraph_insert_and_neighbor_text_change_coexist(fmt: str, tmp_path: Path):
    old = _make(fmt, ["A", "B", "C"])
    new = _make(fmt, ["A", "X", "B updated", "C"])
    plan = build_revision_plan(old, new, everywhere=False)

    assert [(r.kind, r.old_block_index, r.new_block_index) for r in plan.body_paragraphs] == [
        ("insert", None, 1)
    ]
    assert [(p.old_text, p.new_text) for p in plan.paragraphs] == [("B", "B updated")]

    out = tmp_path / f"paragraph-mixed.{fmt}"
    old.compare(new, author="QA", date="2026-10-08T06:00:00Z", everywhere=False).save(out)
    assert _projection(out, fmt, accepted=True) == ["A", "X", "B updated", "C"]
    assert _projection(out, fmt, accepted=False) == ["A", "B", "C"]


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_empty_paragraph_structural_revision(fmt: str, tmp_path: Path):
    old = _make(fmt, ["A", "B"])
    new = _make(fmt, ["A", "", "B"])
    out = tmp_path / f"paragraph-empty.{fmt}"

    old.compare(new, author="QA", date="2026-10-08T06:00:00Z", everywhere=False).save(out)

    assert _projection(out, fmt, accepted=True) == ["A", "", "B"]
    assert _projection(out, fmt, accepted=False) == ["A", "B"]


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_paragraph_insert_before_table_keeps_block_position(fmt: str, tmp_path: Path):
    old = Document.new(fmt)
    old.add_paragraph("A")
    old_table = old.add_table(1, 1, style="Table Grid")
    old_table.cell(0, 0).text = "cell"
    old.add_paragraph("B")

    new = Document.new(fmt)
    new.add_paragraph("A")
    new.add_paragraph("X")
    new_table = new.add_table(1, 1, style="Table Grid")
    new_table.cell(0, 0).text = "cell"
    new.add_paragraph("B")

    out = tmp_path / f"paragraph-before-table.{fmt}"
    old.compare(new, author="QA", date="2026-10-08T06:00:00Z").save(out)

    assert _projection(out, fmt, accepted=True) == ["A", "X", "<TABLE>", "B"]
    assert _projection(out, fmt, accepted=False) == ["A", "<TABLE>", "B"]


def test_docx_paragraph_revision_markup_has_content_and_paragraph_mark(tmp_path: Path):
    old = _make("docx", ["A", "B", "C"])
    new = _make("docx", ["A", "X", "C"])
    # This is a one-for-one text replacement, not a structure change.
    new2 = _make("docx", ["A", "X", "B", "C"])
    out = tmp_path / "docx-paragraph-mark.docx"
    old.compare(new2, author="Alice", date="2026-10-08T06:00:00Z", everywhere=False).save(out)

    with ZipFile(out) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
    ns = {"w": W}
    inserted = root.xpath("./w:body/w:p[w:pPr/w:rPr/w:ins]", namespaces=ns)
    assert len(inserted) == 1
    assert inserted[0].xpath("./w:ins/w:r/w:t/text()", namespaces=ns) == ["X"]
    mark = inserted[0].xpath("./w:pPr/w:rPr/w:ins", namespaces=ns)[0]
    assert mark.get(f"{{{W}}}author") == "Alice"
    assert mark.get(f"{{{W}}}date") == "2026-10-08T06:00:00Z"


@pytest.mark.parametrize("kind", ["insert", "delete"])
def test_hwpx_paragraph_revision_sets_paraend(kind: str, tmp_path: Path):
    if kind == "insert":
        old = _make("hwpx", ["A", "C"])
        new = _make("hwpx", ["A", "B", "C"])
    else:
        old = _make("hwpx", ["A", "B", "C"])
        new = _make("hwpx", ["A", "C"])
    out = tmp_path / f"hwpx-{kind}.hwpx"
    old.compare(new, author="Alice", date="2026-10-08T06:00:00Z", everywhere=False).save(out)

    with ZipFile(out) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
    ns = {"hp": HP}
    ends = root.xpath(f".//hp:{kind}End[@paraend='1']", namespaces=ns)
    assert len(ends) == 1


def test_deleted_complex_docx_paragraph_fails_closed():
    old = Document.new("docx")
    old.add_paragraph("A")
    complex_p = old.add_paragraph()
    complex_p.native.add_run("link ")
    # A drawing is a relationship-bearing run child and must never be copied
    # from the old package into the new package without relationship import.
    from io import BytesIO
    from base64 import b64decode
    png = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZQmcAAAAASUVORK5CYII=")
    complex_p.native.add_run().add_picture(BytesIO(png))
    old.add_paragraph("C")
    new = _make("docx", ["A", "C"])

    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new, everywhere=False)
    assert excinfo.value.code == "compare-unsafe-inline-structure"


def test_table_insertion_remains_fail_closed():
    old = _make("docx", ["A", "B"])
    new = Document.new("docx")
    new.add_paragraph("A")
    new.add_table(1, 1)
    new.add_paragraph("B")

    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new, everywhere=False)
    assert excinfo.value.code == "compare-table-structure-not-supported"

@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_multisection_structural_paragraph_change_fails_closed(fmt: str):
    old = Document.new(fmt)
    old.add_paragraph("A")
    old.add_section()
    old.add_paragraph("B")

    new = Document.new(fmt)
    new.add_paragraph("A")
    new.add_section()
    new.add_paragraph("X")
    new.add_paragraph("B")

    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new, everywhere=False)
    assert excinfo.value.code == "compare-paragraph-section-boundary-unsupported"
