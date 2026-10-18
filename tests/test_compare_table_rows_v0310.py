"""v0.31 DOCX row-level tracked comparison and HWPX fail-closed boundary."""
from __future__ import annotations

from base64 import b64decode
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from lxml import etree

from pywpdoc import Document, DocumentUnsupportedError
from pywpdoc.features.compare import build_revision_plan

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PNG_1PX = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZQmcAAAAASUVORK5CYII="
)


def _table_doc(fmt: str, rows: list[tuple[str, str]]) -> Document:
    doc = Document.new(fmt)
    table = doc.add_table(len(rows), 2, style="Table Grid")
    for index, (left, right) in enumerate(rows):
        table.cell(index, 0).text = left
        table.cell(index, 1).text = right
    return doc


def _row_matrix(doc: Document) -> list[tuple[str, ...]]:
    return [tuple(cell.text for cell in row.cells) for row in doc.tables[0].rows]


def _docx_row_projection(path: Path, *, accepted: bool) -> list[tuple[str, ...]]:
    """Project tracked DOCX table rows as Accept All or Reject All would."""
    with ZipFile(path) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
    ns = {"w": W}
    projected: list[tuple[str, ...]] = []
    rows = root.xpath(".//w:tbl[1]/w:tr", namespaces=ns)
    for row in rows:
        inserted = bool(row.xpath("./w:trPr/w:ins", namespaces=ns))
        deleted = bool(row.xpath("./w:trPr/w:del", namespaces=ns))
        if accepted and deleted:
            continue
        if not accepted and inserted:
            continue

        cells: list[str] = []
        for cell in row.xpath("./w:tc", namespaces=ns):
            parts: list[str] = []
            for paragraph in cell.xpath(".//w:p", namespaces=ns):
                for child in paragraph:
                    name = etree.QName(child).localname
                    if name == "r":
                        parts.extend(t.text or "" for t in child.xpath("./w:t", namespaces=ns))
                    elif name == "ins" and accepted:
                        parts.extend(t.text or "" for t in child.xpath(".//w:t", namespaces=ns))
                    elif name == "del" and not accepted:
                        parts.extend(t.text or "" for t in child.xpath(".//w:delText", namespaces=ns))
            cells.append("".join(parts))
        projected.append(tuple(cells))
    return projected


def _docx_root(path: Path) -> tuple[etree._Element, etree._Element]:
    with ZipFile(path) as zf:
        return (
            etree.fromstring(zf.read("word/document.xml")),
            etree.fromstring(zf.read("word/settings.xml")),
        )


def test_revision_plan_aligns_inserted_row_and_modified_neighbor():
    old = _table_doc("docx", [("A", "1"), ("B", "2"), ("C", "3")])
    new = _table_doc("docx", [("A", "1"), ("X", "9"), ("B", "20"), ("C", "3")])

    plan = build_revision_plan(old, new)

    assert [(r.kind, r.old_row_index, r.new_row_index) for r in plan.table_rows] == [
        ("insert", None, 1)
    ]
    changed = [(p.old_text, p.new_text, p.source_paragraph_index, p.new_paragraph_index) for p in plan.paragraphs]
    assert changed == [("2", "20", 3, 5)]


def test_docx_tracked_row_insert_accept_reject_invariant(tmp_path: Path):
    old = _table_doc("docx", [("A", "1"), ("B", "2"), ("C", "3")])
    new = _table_doc("docx", [("A", "1"), ("X", "9"), ("B", "2"), ("C", "3")])
    old_before = _row_matrix(old)
    new_before = _row_matrix(new)

    out = tmp_path / "row-insert-review.docx"
    old.compare(new, author="Row QA", date="2026-10-08T03:04:05Z").save(out)

    assert _docx_row_projection(out, accepted=True) == new_before
    assert _docx_row_projection(out, accepted=False) == old_before
    assert _row_matrix(old) == old_before
    assert _row_matrix(new) == new_before

    root, settings = _docx_root(out)
    ns = {"w": W}
    row_ins = root.xpath(".//w:tr/w:trPr/w:ins", namespaces=ns)
    assert len(row_ins) == 1
    assert row_ins[0].get(f"{{{W}}}author") == "Row QA"
    assert row_ins[0].get(f"{{{W}}}date") == "2026-10-08T03:04:05Z"
    assert len(settings.xpath("./w:trackRevisions", namespaces=ns)) == 1


def test_docx_tracked_row_delete_accept_reject_invariant(tmp_path: Path):
    old = _table_doc("docx", [("A", "1"), ("B", "2"), ("C", "3")])
    new = _table_doc("docx", [("A", "1"), ("C", "3")])
    old_before = _row_matrix(old)
    new_before = _row_matrix(new)

    out = tmp_path / "row-delete-review.docx"
    old.compare(new, author="Row QA", date="2026-10-08T03:04:05Z").save(out)

    assert _docx_row_projection(out, accepted=True) == new_before
    assert _docx_row_projection(out, accepted=False) == old_before
    root, _ = _docx_root(out)
    ns = {"w": W}
    deleted = root.xpath(".//w:tr[w:trPr/w:del]", namespaces=ns)
    assert len(deleted) == 1
    assert "B" in "".join(deleted[0].xpath(".//w:t/text()", namespaces=ns))


def test_docx_row_change_and_cell_text_change_coexist(tmp_path: Path):
    old = _table_doc("docx", [("A", "1"), ("B", "2"), ("C", "3")])
    new = _table_doc("docx", [("A", "1"), ("X", "9"), ("B", "20"), ("C", "3")])

    out = tmp_path / "mixed-row-and-text.docx"
    old.compare(new, author="Mixed QA", date="2026-10-08T00:00:00Z").save(out)

    assert _docx_row_projection(out, accepted=True) == _row_matrix(new)
    assert _docx_row_projection(out, accepted=False) == _row_matrix(old)
    root, _ = _docx_root(out)
    ns = {"w": W}
    assert len(root.xpath(".//w:tr/w:trPr/w:ins", namespaces=ns)) == 1
    # The B quantity changed 2 -> 20, so the inline insertion is independent
    # of the row-level insertion marker.
    assert len(root.xpath(".//w:p/w:ins", namespaces=ns)) >= 1


def test_docx_multiple_adjacent_row_deletions_preserve_order(tmp_path: Path):
    old = _table_doc("docx", [("A", "1"), ("B", "2"), ("C", "3"), ("D", "4")])
    new = _table_doc("docx", [("A", "1"), ("D", "4")])
    out = tmp_path / "multi-delete.docx"

    old.compare(new, author="QA", date="2026-10-08T00:00:00Z").save(out)

    assert _docx_row_projection(out, accepted=True) == _row_matrix(new)
    assert _docx_row_projection(out, accepted=False) == _row_matrix(old)
    root, _ = _docx_root(out)
    ns = {"w": W}
    deleted = root.xpath(".//w:tr[w:trPr/w:del]", namespaces=ns)
    labels = ["".join(row.xpath(".//w:t/text()", namespaces=ns)) for row in deleted]
    assert labels == ["B2", "C3"]


def test_docx_multiple_adjacent_row_insertions_preserve_order(tmp_path: Path):
    old = _table_doc("docx", [("A", "1"), ("D", "4")])
    new = _table_doc("docx", [("A", "1"), ("B", "2"), ("C", "3"), ("D", "4")])
    out = tmp_path / "multi-insert.docx"

    old.compare(new, author="QA", date="2026-10-08T00:00:00Z").save(out)

    assert _docx_row_projection(out, accepted=True) == _row_matrix(new)
    assert _docx_row_projection(out, accepted=False) == _row_matrix(old)
    root, _ = _docx_root(out)
    ns = {"w": W}
    inserted = root.xpath(".//w:tr[w:trPr/w:ins]", namespaces=ns)
    labels = ["".join(row.xpath(".//w:t/text()", namespaces=ns)) for row in inserted]
    assert labels == ["B2", "C3"]


@pytest.mark.parametrize(
    ("old_rows", "new_rows"),
    [
        ([("A", "1"), ("B", "2")], [("A", "1"), ("X", "9"), ("B", "2")]),
        ([("A", "1"), ("B", "2")], [("A", "1")]),
    ],
)
def test_hwpx_row_structure_change_fails_closed_without_mutation(old_rows, new_rows):
    old = _table_doc("hwpx", old_rows)
    new = _table_doc("hwpx", new_rows)
    old_before = _row_matrix(old)
    new_before = _row_matrix(new)

    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new, author="QA")

    assert excinfo.value.code == "compare-hwpx-table-row-track-unsupported"
    assert _row_matrix(old) == old_before
    assert _row_matrix(new) == new_before


def test_docx_deleted_relationship_bearing_row_fails_closed():
    old = Document.new("docx")
    old_table = old.add_table(2, 1, style="Table Grid")
    old_table.cell(0, 0).paragraphs[0].native.add_run().add_picture(BytesIO(PNG_1PX))
    old_table.cell(1, 0).text = "keep"
    new = Document.new("docx")
    new_table = new.add_table(1, 1, style="Table Grid")
    new_table.cell(0, 0).text = "keep"

    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new)
    assert excinfo.value.code == "compare-table-row-external-reference-unsupported"


def test_docx_deleted_vertical_merge_row_fails_closed():
    old = Document.new("docx")
    old_table = old.add_table(3, 2, style="Table Grid")
    old_table.cell(0, 0).text = "A"
    old_table.cell(1, 0).merge(old_table.cell(2, 0)).text = "merged"
    old_table.cell(1, 1).text = "remove"
    old_table.cell(2, 1).text = "tail"

    # Keep only the first row in the new document; the deleted material includes
    # a vertical merge and therefore must not be copied speculatively.
    new = _table_doc("docx", [("A", "")])

    with pytest.raises(DocumentUnsupportedError) as excinfo:
        old.compare(new)
    assert excinfo.value.code == "compare-table-row-vertical-merge-unsupported"


def test_docx_same_structure_vertical_merge_keeps_v029_text_compare_behavior(tmp_path: Path):
    old = Document.new("docx")
    new = Document.new("docx")
    for doc, value in ((old, "old"), (new, "new")):
        table = doc.add_table(3, 2, style="Table Grid")
        table.cell(0, 0).text = "A"
        table.cell(1, 0).merge(table.cell(2, 0)).text = "merged"
        table.cell(1, 1).text = value
        table.cell(2, 1).text = "tail"

    out = tmp_path / "vertical-merge-text-only.docx"
    old.compare(new, author="QA", date="2026-10-08T00:00:00Z").save(out)

    root, _ = _docx_root(out)
    ns = {"w": W}
    assert not root.xpath(".//w:tr/w:trPr/w:ins | .//w:tr/w:trPr/w:del", namespaces=ns)
    assert root.xpath(".//w:p/w:ins", namespaces=ns)
    assert root.xpath(".//w:p/w:del", namespaces=ns)
