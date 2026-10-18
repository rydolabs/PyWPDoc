"""v0.29 tracked comparison: conservative text revisions without regressions."""
from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest
from lxml import etree

from pywpdoc import Document, DocumentUnsupportedError, DocumentValueError
from pywpdoc.features.compare import build_revision_plan

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HH = "http://www.hancom.co.kr/hwpml/2011/head"


def _doc_pair(fmt: str, old_text: str, new_text: str):
    old = Document.new(fmt)
    new = Document.new(fmt)
    old.add_paragraph(old_text)
    new.add_paragraph(new_text)
    return old, new


def _docx_projection(path: Path, *, accepted: bool) -> str:
    with ZipFile(path) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
    ns = {"w": W}
    paragraphs: list[str] = []
    for paragraph in root.xpath(".//w:p", namespaces=ns):
        parts: list[str] = []
        for child in paragraph:
            name = etree.QName(child).localname
            if name == "r":
                parts.extend(t.text or "" for t in child.xpath("./w:t", namespaces=ns))
            elif name == "ins" and accepted:
                parts.extend(t.text or "" for t in child.xpath(".//w:t", namespaces=ns))
            elif name == "del" and not accepted:
                parts.extend(t.text or "" for t in child.xpath(".//w:delText", namespaces=ns))
        paragraphs.append("".join(parts))
    return "\n".join(paragraphs)


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
            keep = state == "plain" or (state == "insert" and accepted) or (state == "delete" and not accepted)
            if keep:
                parts.append(child.tail)
    return "".join(parts)


def _hwpx_projection(path: Path, *, accepted: bool) -> str:
    with ZipFile(path) as zf:
        root = etree.fromstring(zf.read("Contents/section0.xml"))
    ns = {"hp": HP}
    paragraphs: list[str] = []
    for paragraph in root.xpath(".//hp:p", namespaces=ns):
        text = "".join(
            _hwpx_t_projection(t, accepted=accepted)
            for t in paragraph.xpath("./hp:run/hp:t", namespaces=ns)
        )
        paragraphs.append(text)
    return "\n".join(paragraphs).strip("\n")


def _projection(path: Path, fmt: str, *, accepted: bool) -> str:
    if fmt == "docx":
        return _docx_projection(path, accepted=accepted)
    return _hwpx_projection(path, accepted=accepted)


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_compare_tracks_replace_and_accept_reject_invariant(fmt: str, tmp_path: Path):
    old, new = _doc_pair(fmt, "계약기간은 1년이다.", "계약기간은 2년이다.")
    review = old.compare(
        new,
        author="PyWPDoc QA",
        date="2026-10-08T00:00:00Z",
        everywhere=False,
    )
    out = tmp_path / f"review.{fmt}"
    review.save(out)

    assert _projection(out, fmt, accepted=True) == "계약기간은 2년이다."
    assert _projection(out, fmt, accepted=False) == "계약기간은 1년이다."
    # compare must be non-destructive to both inputs.
    assert old.paragraphs[0].text == "계약기간은 1년이다."
    assert new.paragraphs[0].text == "계약기간은 2년이다."


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_compare_tracks_insert_and_delete_in_one_paragraph(fmt: str, tmp_path: Path):
    old, new = _doc_pair(fmt, "alpha beta gamma", "alpha bright gamma!")
    review = old.compare(new, author="Reviewer", date="2026-10-08T01:02:03Z", everywhere=False)
    out = tmp_path / f"mixed.{fmt}"
    review.save(out)

    assert _projection(out, fmt, accepted=True) == "alpha bright gamma!"
    assert _projection(out, fmt, accepted=False) == "alpha beta gamma"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_compare_same_structure_table_cell_text(fmt: str, tmp_path: Path):
    old = Document.new(fmt)
    new = Document.new(fmt)
    old_table = old.add_table(1, 2, style="Table Grid")
    new_table = new.add_table(1, 2, style="Table Grid")
    old_table.cell(0, 0).text = "품목"
    old_table.cell(0, 1).text = "100"
    new_table.cell(0, 0).text = "품목"
    new_table.cell(0, 1).text = "120"

    review = old.compare(new, author="Table QA", date="2026-10-08T00:00:00Z")
    out = tmp_path / f"table-review.{fmt}"
    review.save(out)

    accepted = _projection(out, fmt, accepted=True)
    rejected = _projection(out, fmt, accepted=False)
    assert "120" in accepted and "100" not in accepted
    assert "100" in rejected and "120" not in rejected


def test_docx_revision_metadata_and_track_revisions_flag(tmp_path: Path):
    old, new = _doc_pair("docx", "A1", "A2")
    out = tmp_path / "meta.docx"
    old.compare(new, author="Alice", date="2026-10-08T12:34:56Z", everywhere=False).save(out)

    with ZipFile(out) as zf:
        document = etree.fromstring(zf.read("word/document.xml"))
        settings = etree.fromstring(zf.read("word/settings.xml"))
    ns = {"w": W}
    revisions = document.xpath(".//w:ins | .//w:del", namespaces=ns)
    assert {etree.QName(node).localname for node in revisions} == {"ins", "del"}
    assert all(node.get(f"{{{W}}}author") == "Alice" for node in revisions)
    assert all(node.get(f"{{{W}}}date") == "2026-10-08T12:34:56Z" for node in revisions)
    assert len(settings.xpath("./w:trackRevisions", namespaces=ns)) == 1


def test_hwpx_revision_metadata_and_markers(tmp_path: Path):
    old, new = _doc_pair("hwpx", "A1", "A2")
    out = tmp_path / "meta.hwpx"
    old.compare(new, author="Alice", date="2026-10-08T12:34:56Z", everywhere=False).save(out)

    with ZipFile(out) as zf:
        section = etree.fromstring(zf.read("Contents/section0.xml"))
        header = etree.fromstring(zf.read("Contents/header.xml"))
    hp = {"hp": HP}
    hh = {"hh": HH}
    assert len(section.xpath(".//hp:insertBegin", namespaces=hp)) == 1
    assert len(section.xpath(".//hp:insertEnd", namespaces=hp)) == 1
    assert len(section.xpath(".//hp:deleteBegin", namespaces=hp)) == 1
    assert len(section.xpath(".//hp:deleteEnd", namespaces=hp)) == 1

    authors = header.xpath(".//hh:trackChangeAuthors/hh:trackChangeAuthor", namespaces=hh)
    changes = header.xpath(".//hh:trackChanges/hh:trackChange", namespaces=hh)
    assert len(authors) == 1 and authors[0].get("name") == "Alice"
    assert {node.get("type") for node in changes} == {"Insert", "Delete"}
    assert all(node.get("date") == "2026-10-08T12:34:56Z" for node in changes)
    assert all(node.get("authorID") == authors[0].get("id") for node in changes)

    # Existing HWPX validation + reopen must accept the generated package.
    reopened = Document.open(out)
    assert reopened.format == "hwpx"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_noop_compare_is_revision_free_copy(fmt: str, tmp_path: Path):
    old, new = _doc_pair(fmt, "unchanged", "unchanged")
    review = old.compare(new, everywhere=False)
    assert review is not new
    assert review.backend is not new.backend
    out = tmp_path / f"noop.{fmt}"
    review.save(out)

    with ZipFile(out) as zf:
        if fmt == "docx":
            document = zf.read("word/document.xml")
            settings = zf.read("word/settings.xml")
            assert b"<w:ins" not in document and b"<w:del" not in document
            assert b"trackRevisions" not in settings
        else:
            section = zf.read("Contents/section0.xml")
            header = zf.read("Contents/header.xml")
            assert b"insertBegin" not in section and b"deleteBegin" not in section
            assert b"<hh:trackChanges" not in header
    assert _projection(out, fmt, accepted=True) == "unchanged"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_structural_paragraph_change_is_supported_since_v0320(fmt: str, tmp_path: Path):
    old = Document.new(fmt)
    old.add_paragraph("first")
    new = Document.new(fmt)
    new.add_paragraph("first")
    new.add_paragraph("second")

    review = old.compare(new, everywhere=False)
    out = tmp_path / f"structural-paragraph.{fmt}"
    review.save(out)
    assert out.exists()
    assert old.paragraphs[-1].text == "first"
    assert new.paragraphs[-1].text == "second"


def test_cross_format_compare_is_rejected():
    old, _ = _doc_pair("docx", "same", "same")
    _, new = _doc_pair("hwpx", "same", "same")
    with pytest.raises(DocumentValueError) as excinfo:
        old.compare(new, everywhere=False)
    assert excinfo.value.code == "compare-format-mismatch"


def test_docx_changed_complex_inline_structure_fails_closed():
    old = Document.new("docx")
    new = Document.new("docx")
    old_p = old.add_paragraph()
    new_p = new.add_paragraph()
    old_p.add_run("A").add_tab()
    old_p.add_run("1")
    new_p.add_run("A").add_tab()
    new_p.add_run("2")

    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new, everywhere=False)
    assert excinfo.value.code == "compare-unsafe-inline-structure"


def test_revision_plan_is_backend_neutral_and_only_contains_changed_paragraphs():
    old = Document.new("docx")
    new = Document.new("docx")
    old.add_paragraph("same")
    old.add_paragraph("old")
    new.add_paragraph("same")
    new.add_paragraph("new")

    plan = build_revision_plan(old, new, everywhere=False)
    assert plan.format == "docx"
    assert plan.change_count == 1
    assert [p.paragraph_index for p in plan.paragraphs] == [1]
    assert plan.paragraphs[0].old_text == "old"
    assert plan.paragraphs[0].new_text == "new"
