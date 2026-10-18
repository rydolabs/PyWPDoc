"""DOCX tracked-revision writer used by the optional compare feature."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Iterable

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from ..core.errors import DocumentUnsupportedError
from .traversal import iter_search_paragraphs

_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def _local(element: Any) -> str:
    tag = getattr(element, "tag", "")
    return tag.rsplit("}", 1)[-1] if "}" in str(tag) else str(tag)


def _revision_date(value: str | None) -> str:
    if value:
        return str(value)
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _paragraphs(document: Any, everywhere: bool) -> list[Any]:
    return list(iter_search_paragraphs(document)) if everywhere else list(document.paragraphs)


def _assert_plain_paragraph(paragraph: Any, index: int) -> None:
    for child in paragraph._p:
        name = _local(child)
        if name == "pPr":
            continue
        if name != "r":
            raise DocumentUnsupportedError(
                "tracked-text compare found unsupported inline structure in DOCX paragraph",
                code="compare-unsafe-inline-structure",
                context={"paragraph_index": index, "element": name, "format": "docx"},
            )
        for run_child in child:
            run_name = _local(run_child)
            if run_name not in {"rPr", "t"}:
                raise DocumentUnsupportedError(
                    "tracked-text compare supports plain DOCX text runs only in changed paragraphs",
                    code="compare-unsafe-inline-structure",
                    context={"paragraph_index": index, "element": run_name, "format": "docx"},
                )


def _run_records(paragraph: Any) -> list[tuple[int, int, Any, str]]:
    records: list[tuple[int, int, Any, str]] = []
    offset = 0
    for run in paragraph._p:
        if _local(run) != "r":
            continue
        text = "".join((child.text or "") for child in run if _local(child) == "t")
        if not text:
            continue
        start = offset
        offset += len(text)
        records.append((start, offset, run, text))
    return records


def _text_element(name: str, text: str) -> Any:
    node = OxmlElement(name)
    node.text = text
    if text[:1].isspace() or text[-1:].isspace():
        node.set(_XML_SPACE, "preserve")
    return node


def _slice_runs(paragraph: Any, start: int, end: int, *, deleted: bool = False) -> list[Any]:
    if start == end:
        return []
    out: list[Any] = []
    for r_start, r_end, source, text in _run_records(paragraph):
        if r_end <= start or r_start >= end:
            continue
        local_start = max(start, r_start) - r_start
        local_end = min(end, r_end) - r_start
        piece = text[local_start:local_end]
        if not piece:
            continue
        run = OxmlElement("w:r")
        rpr = next((c for c in source if _local(c) == "rPr"), None)
        if rpr is not None:
            run.append(deepcopy(rpr))
        run.append(_text_element("w:delText" if deleted else "w:t", piece))
        out.append(run)
    if not out:
        raise DocumentUnsupportedError(
            "tracked-text compare could not map text range back to DOCX runs",
            code="compare-text-map-failed",
            context={"start": start, "end": end, "format": "docx"},
        )
    return out


def _next_revision_id(document: Any) -> int:
    maximum = -1
    wid = qn("w:id")
    for element in document.element.iter():
        if _local(element) not in {"ins", "del", "rPrChange", "pPrChange"}:
            continue
        value = element.get(wid)
        try:
            maximum = max(maximum, int(value))
        except (TypeError, ValueError):
            continue
    return maximum + 1


def _revision_container(kind: str, runs: Iterable[Any], rev_id: int, author: str, date: str) -> Any:
    container = OxmlElement(f"w:{kind}")
    container.set(qn("w:id"), str(rev_id))
    container.set(qn("w:author"), author)
    container.set(qn("w:date"), date)
    for run in runs:
        container.append(run)
    return container


def _track_change_element(kind: str, rev_id: int, author: str, date: str) -> Any:
    node = OxmlElement(f"w:{kind}")
    node.set(qn("w:id"), str(rev_id))
    node.set(qn("w:author"), author)
    node.set(qn("w:date"), date)
    return node


def _enable_track_revisions(document: Any) -> None:
    settings = document.settings.element
    if settings.find(qn("w:trackRevisions")) is None:
        settings.append(OxmlElement("w:trackRevisions"))


def _body_blocks(document: Any) -> list[Any]:
    return list(document.iter_inner_content())


def _is_paragraph_block(block: Any) -> bool:
    return "paragraph" in type(block).__name__.lower()


def _assert_structural_paragraph_safe(paragraph: Any, index: int) -> None:
    _assert_plain_paragraph(paragraph, index)
    ppr = paragraph._p.find(qn("w:pPr"))
    if ppr is not None and ppr.find(qn("w:sectPr")) is not None:
        raise DocumentUnsupportedError(
            "paragraph structural revisions across section-break carriers are not supported",
            code="compare-paragraph-section-boundary-unsupported",
            context={"block_index": index, "format": "docx"},
        )


def _paragraph_mark_revision(ppr: Any, kind: str, rev_id: int, author: str, date: str) -> None:
    rpr = ppr.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        ppr.append(rpr)
    if any(_local(child) in {"ins", "del"} for child in rpr):
        raise DocumentUnsupportedError(
            "paragraph mark already contains a tracked insertion/deletion",
            code="compare-existing-revisions-unsupported",
        )
    rpr.append(_track_change_element(kind, rev_id, author, date))


def _whole_paragraph_runs(paragraph: Any, *, deleted: bool) -> list[Any]:
    out: list[Any] = []
    for source in paragraph._p:
        if _local(source) != "r":
            continue
        run = OxmlElement("w:r")
        rpr = next((c for c in source if _local(c) == "rPr"), None)
        if rpr is not None:
            run.append(deepcopy(rpr))
        had_text = False
        for child in source:
            if _local(child) != "t":
                continue
            text = child.text or ""
            run.append(_text_element("w:delText" if deleted else "w:t", text))
            had_text = True
        if had_text:
            out.append(run)
    return out


def _mark_whole_paragraph(
    paragraph: Any,
    *,
    kind: str,
    rev_id: int,
    author: str,
    date: str,
    block_index: int,
) -> int:
    _assert_structural_paragraph_safe(paragraph, block_index)
    ppr = next((deepcopy(c) for c in paragraph._p if _local(c) == "pPr"), None)
    if ppr is None:
        ppr = OxmlElement("w:pPr")
    runs = _whole_paragraph_runs(paragraph, deleted=kind == "del")
    rebuilt: list[Any] = [ppr]
    if runs:
        rebuilt.append(_revision_container(kind, runs, rev_id, author, date))
        rev_id += 1
    _paragraph_mark_revision(ppr, kind, rev_id, author, date)
    rev_id += 1
    paragraph._p[:] = rebuilt
    return rev_id


def _insert_body_paragraph(document: Any, index: int, paragraph_element: Any) -> None:
    blocks = _body_blocks(document)
    if not 0 <= index <= len(blocks):
        raise DocumentUnsupportedError(
            "paragraph insertion anchor moved while applying revisions",
            code="compare-paragraph-alignment-ambiguous",
            context={"block_index": index, "block_count": len(blocks), "format": "docx"},
        )
    if index < len(blocks):
        anchor = blocks[index]
        element = anchor._p if _is_paragraph_block(anchor) else anchor._tbl
        element.addprevious(paragraph_element)
        return
    body = document.element.body
    sectpr = body.find(qn("w:sectPr"))
    if sectpr is not None:
        sectpr.addprevious(paragraph_element)
    else:
        body.append(paragraph_element)


def _apply_body_paragraph_revisions(
    document: Any,
    old_document: Any,
    revisions: Iterable[Any],
    *,
    rev_id: int,
    author: str,
    date: str,
) -> int:
    revisions = list(revisions)
    if not revisions:
        return rev_id
    new_blocks = _body_blocks(document)
    old_blocks = _body_blocks(old_document)

    # Mark new paragraphs before deleted old paragraphs are materialized so
    # plan block indices still address the pristine new-document block list.
    for revision in revisions:
        if revision.kind != "insert":
            continue
        try:
            block = new_blocks[int(revision.new_block_index)]
        except IndexError as exc:
            raise DocumentUnsupportedError(
                "new paragraph moved while applying tracked insertion",
                code="compare-paragraph-alignment-ambiguous",
                context={"block_index": revision.new_block_index, "format": "docx"},
            ) from exc
        if not _is_paragraph_block(block):
            raise DocumentUnsupportedError(
                "tracked paragraph insertion no longer points to a paragraph",
                code="compare-paragraph-alignment-ambiguous",
                context={"block_index": revision.new_block_index, "format": "docx"},
            )
        rev_id = _mark_whole_paragraph(
            block, kind="ins", rev_id=rev_id, author=author, date=date,
            block_index=int(revision.new_block_index),
        )

    offset = 0
    from docx.text.paragraph import Paragraph as NativeParagraph
    for revision in revisions:
        if revision.kind != "delete":
            continue
        source_index = revision.old_block_index
        if source_index is None:
            raise DocumentUnsupportedError(
                "deleted paragraph revision is missing its old source block",
                code="compare-paragraph-alignment-ambiguous",
            )
        try:
            source = old_blocks[int(source_index)]
        except IndexError as exc:
            raise DocumentUnsupportedError(
                "old paragraph moved while applying tracked deletion",
                code="compare-paragraph-alignment-ambiguous",
                context={"block_index": source_index, "format": "docx"},
            ) from exc
        if not _is_paragraph_block(source):
            raise DocumentUnsupportedError(
                "tracked paragraph deletion source is not a paragraph",
                code="compare-paragraph-alignment-ambiguous",
                context={"block_index": source_index, "format": "docx"},
            )
        _assert_structural_paragraph_safe(source, int(source_index))
        copied = deepcopy(source._p)
        copied_paragraph = NativeParagraph(copied, document)
        rev_id = _mark_whole_paragraph(
            copied_paragraph, kind="del", rev_id=rev_id, author=author, date=date,
            block_index=int(source_index),
        )
        actual_index = int(revision.new_block_index) + offset
        _insert_body_paragraph(document, actual_index, copied)
        offset += 1
    return rev_id


def _clean_property_copy(element: Any, *, change_name: str, drop_sectpr: bool = False) -> Any:
    if element is None:
        return None
    copied = deepcopy(element)
    for child in list(copied):
        name = _local(child)
        if name == change_name or (drop_sectpr and name == "sectPr"):
            copied.remove(child)
    return copied


def _ensure_no_existing_property_change(element: Any, change_name: str, *, context: dict[str, Any]) -> None:
    if element is None:
        return
    if any(_local(node) == change_name for node in element.iter()):
        raise DocumentUnsupportedError(
            "format properties already contain tracked formatting revisions",
            code="compare-existing-revisions-unsupported",
            context=context,
        )


def _paragraph_format_change_element(old_ppr: Any, rev_id: int, author: str, date: str) -> Any:
    change = OxmlElement("w:pPrChange")
    change.set(qn("w:id"), str(rev_id))
    change.set(qn("w:author"), author)
    change.set(qn("w:date"), date)
    old_props = _clean_property_copy(old_ppr, change_name="pPrChange", drop_sectpr=True)
    if old_props is None:
        old_props = OxmlElement("w:pPr")
    change.append(old_props)
    return change


def _run_format_change_element(old_rpr: Any, rev_id: int, author: str, date: str) -> Any:
    change = OxmlElement("w:rPrChange")
    change.set(qn("w:id"), str(rev_id))
    change.set(qn("w:author"), author)
    change.set(qn("w:date"), date)
    old_props = _clean_property_copy(old_rpr, change_name="rPrChange")
    if old_props is None:
        old_props = OxmlElement("w:rPr")
    change.append(old_props)
    return change


def _old_run_rpr_at(paragraph: Any, position: int) -> Any:
    for start, end, source, _text in _run_records(paragraph):
        if start <= position < end:
            rpr = next((c for c in source if _local(c) == "rPr"), None)
            _ensure_no_existing_property_change(
                rpr, "rPrChange", context={"format": "docx", "position": position},
            )
            return rpr
    return None


def _apply_paragraph_format_revisions(
    output_paragraphs: list[Any], old_paragraphs: list[Any], revisions: Iterable[Any],
    *, rev_id: int, author: str, date: str,
) -> int:
    for revision in revisions:
        new_index = int(revision.paragraph_index)
        old_index = int(revision.old_paragraph_index)
        try:
            out_p = output_paragraphs[new_index]
            old_p = old_paragraphs[old_index]
        except IndexError as exc:
            raise DocumentUnsupportedError(
                "paragraph moved while applying tracked paragraph formatting",
                code="compare-format-alignment-ambiguous",
                context={"new_paragraph_index": new_index, "old_paragraph_index": old_index},
            ) from exc
        _assert_plain_paragraph(out_p, new_index)
        _assert_plain_paragraph(old_p, old_index)
        out_ppr = out_p._p.find(qn("w:pPr"))
        old_ppr = old_p._p.find(qn("w:pPr"))
        _ensure_no_existing_property_change(
            out_ppr, "pPrChange", context={"format": "docx", "paragraph_index": new_index},
        )
        _ensure_no_existing_property_change(
            old_ppr, "pPrChange", context={"format": "docx", "paragraph_index": old_index},
        )
        if out_ppr is None:
            out_ppr = OxmlElement("w:pPr")
            out_p._p.insert(0, out_ppr)
        out_ppr.append(_paragraph_format_change_element(old_ppr, rev_id, author, date))
        rev_id += 1
    return rev_id


def _apply_run_format_revisions(
    output_paragraphs: list[Any], old_paragraphs: list[Any], revisions: Iterable[Any],
    *, rev_id: int, author: str, date: str,
) -> int:
    grouped: dict[int, list[Any]] = {}
    for revision in revisions:
        grouped.setdefault(int(revision.paragraph_index), []).append(revision)

    for new_index in sorted(grouped):
        items = sorted(grouped[new_index], key=lambda item: (item.new_start, item.new_end))
        old_indices = {int(item.old_paragraph_index) for item in items}
        if len(old_indices) != 1:
            raise DocumentUnsupportedError(
                "run-format revisions for one paragraph map to multiple old paragraphs",
                code="compare-format-alignment-ambiguous",
                context={"paragraph_index": new_index},
            )
        old_index = next(iter(old_indices))
        try:
            out_p = output_paragraphs[new_index]
            old_p = old_paragraphs[old_index]
        except IndexError as exc:
            raise DocumentUnsupportedError(
                "paragraph moved while applying tracked run formatting",
                code="compare-format-alignment-ambiguous",
                context={"new_paragraph_index": new_index, "old_paragraph_index": old_index},
            ) from exc
        _assert_plain_paragraph(out_p, new_index)
        _assert_plain_paragraph(old_p, old_index)

        # Validate non-overlap. The planner splits at both old/new run boundaries.
        previous_end = -1
        for item in items:
            if item.new_start < previous_end or item.new_start >= item.new_end:
                raise DocumentUnsupportedError(
                    "run-format revision ranges overlap or are empty",
                    code="compare-format-map-failed",
                    context={"paragraph_index": new_index},
                )
            previous_end = item.new_end

        ppr = out_p._p.find(qn("w:pPr"))
        rebuilt: list[Any] = []
        if ppr is not None:
            rebuilt.append(ppr)

        offset = 0
        item_index = 0
        for source in list(out_p._p):
            if _local(source) == "pPr":
                continue
            if _local(source) != "r":
                raise DocumentUnsupportedError(
                    "tracked run formatting found unsupported inline structure",
                    code="compare-unsafe-inline-structure",
                    context={"paragraph_index": new_index, "format": "docx"},
                )
            text = "".join((child.text or "") for child in source if _local(child) == "t")
            if not text:
                rebuilt.append(deepcopy(source))
                continue
            run_start, run_end = offset, offset + len(text)
            offset = run_end
            boundaries = {run_start, run_end}
            for item in items:
                if item.new_end <= run_start or item.new_start >= run_end:
                    continue
                boundaries.add(max(run_start, int(item.new_start)))
                boundaries.add(min(run_end, int(item.new_end)))
            cuts = sorted(boundaries)
            for seg_start, seg_end in zip(cuts, cuts[1:]):
                if seg_start == seg_end:
                    continue
                local_start = seg_start - run_start
                local_end = seg_end - run_start
                piece = text[local_start:local_end]
                run = OxmlElement("w:r")
                source_rpr = next((c for c in source if _local(c) == "rPr"), None)
                _ensure_no_existing_property_change(
                    source_rpr, "rPrChange",
                    context={"format": "docx", "paragraph_index": new_index},
                )
                new_rpr = _clean_property_copy(source_rpr, change_name="rPrChange")

                target = next((
                    item for item in items
                    if int(item.new_start) <= seg_start and seg_end <= int(item.new_end)
                ), None)
                if target is not None:
                    if new_rpr is None:
                        new_rpr = OxmlElement("w:rPr")
                    old_pos = int(target.old_start) + (seg_start - int(target.new_start))
                    old_rpr = _old_run_rpr_at(old_p, old_pos)
                    new_rpr.append(_run_format_change_element(old_rpr, rev_id, author, date))
                    rev_id += 1
                if new_rpr is not None:
                    run.append(new_rpr)
                run.append(_text_element("w:t", piece))
                rebuilt.append(run)
        out_p._p[:] = rebuilt
    return rev_id


def _assert_row_copy_safe(tr: Any, *, table_index: int, row_index: int) -> None:
    """Reject deleted-row copies that depend on source-document relationships.

    A deleted row is materialized from the old document into the review copy.
    Plain table XML is safe to deep-copy; relationship-bearing content (images,
    hyperlinks, embedded objects) needs an explicit rel-import layer and is
    therefore deferred rather than silently producing dangling references.
    """
    relationship_attrs = {qn("r:id"), qn("r:embed"), qn("r:link")}
    unsafe_names = {
        "bookmarkStart", "bookmarkEnd", "commentRangeStart", "commentRangeEnd",
        "commentReference", "fldChar", "sdt",
    }
    for node in tr.iter():
        if _local(node) in unsafe_names:
            raise DocumentUnsupportedError(
                "deleted DOCX row contains a control structure that cannot be imported safely",
                code="compare-table-row-copy-unsafe",
                context={"table_index": table_index, "row_index": row_index, "element": _local(node)},
            )
        if any(attr in node.attrib for attr in relationship_attrs):
            raise DocumentUnsupportedError(
                "deleted DOCX row contains an external relationship that cannot be imported safely yet",
                code="compare-table-row-external-reference-unsupported",
                context={"table_index": table_index, "row_index": row_index, "element": _local(node)},
            )
        if _local(node) in {"ins", "del", "moveFrom", "moveTo"}:
            raise DocumentUnsupportedError(
                "row already contains tracked revisions and cannot be nested into a new row revision",
                code="compare-existing-revisions-unsupported",
                context={"table_index": table_index, "row_index": row_index},
            )
    if list(tr.iterdescendants(qn("w:vMerge"))):
        raise DocumentUnsupportedError(
            "tracked row deletion across vertical merges is not supported",
            code="compare-table-row-vertical-merge-unsupported",
            context={"table_index": table_index, "row_index": row_index},
        )


def _row_trpr(tr: Any) -> Any:
    trpr = tr.find(qn("w:trPr"))
    if trpr is None:
        trpr = OxmlElement("w:trPr")
        tr.insert(0, trpr)
    return trpr


def _mark_row_revision(tr: Any, kind: str, rev_id: int, author: str, date: str) -> None:
    trpr = _row_trpr(tr)
    for child in trpr:
        if _local(child) in {"ins", "del"}:
            raise DocumentUnsupportedError(
                "table row already has a tracked insertion/deletion marker",
                code="compare-existing-revisions-unsupported",
            )
    trpr.append(_track_change_element(kind, rev_id, author, date))


def _insert_tr(table: Any, index: int, tr: Any) -> None:
    rows = list(table.rows)
    if not 0 <= index <= len(rows):
        raise DocumentUnsupportedError(
            "tracked row insertion anchor moved while applying revisions",
            code="compare-table-row-alignment-ambiguous",
            context={"row_index": index, "row_count": len(rows)},
        )
    if index < len(rows):
        rows[index]._tr.addprevious(tr)
    elif rows:
        rows[-1]._tr.addnext(tr)
    else:
        table._tbl.append(tr)


def _apply_table_row_revisions(
    document: Any,
    old_document: Any,
    revisions: Iterable[Any],
    *,
    rev_id: int,
    author: str,
    date: str,
) -> int:
    grouped: dict[int, list[Any]] = {}
    for revision in revisions:
        grouped.setdefault(int(revision.table_index), []).append(revision)

    new_tables = list(document.tables)
    old_tables = list(old_document.tables)
    for table_index in sorted(grouped):
        try:
            new_table = new_tables[table_index]
            old_table = old_tables[table_index]
        except IndexError as exc:
            raise DocumentUnsupportedError(
                "table alignment changed while applying row revisions",
                code="compare-table-structure-not-supported",
                context={"table_index": table_index},
            ) from exc

        offset = 0
        for revision in grouped[table_index]:
            if revision.kind == "delete":
                source_index = revision.old_row_index
                if source_index is None:
                    raise DocumentUnsupportedError(
                        "deleted row revision is missing its old-row source index",
                        code="compare-table-row-alignment-ambiguous",
                    )
                try:
                    source_tr = old_table.rows[source_index]._tr
                except IndexError as exc:
                    raise DocumentUnsupportedError(
                        "old table row moved while applying tracked deletion",
                        code="compare-table-row-alignment-ambiguous",
                        context={"table_index": table_index, "row_index": source_index},
                    ) from exc
                _assert_row_copy_safe(source_tr, table_index=table_index, row_index=source_index)
                copied = deepcopy(source_tr)
                actual_index = int(revision.new_row_index) + offset
                _mark_row_revision(copied, "del", rev_id, author, date)
                rev_id += 1
                _insert_tr(new_table, actual_index, copied)
                offset += 1
            elif revision.kind == "insert":
                actual_index = int(revision.new_row_index) + offset
                try:
                    tr = new_table.rows[actual_index]._tr
                except IndexError as exc:
                    raise DocumentUnsupportedError(
                        "new table row moved while applying tracked insertion",
                        code="compare-table-row-alignment-ambiguous",
                        context={"table_index": table_index, "row_index": revision.new_row_index},
                    ) from exc
                _mark_row_revision(tr, "ins", rev_id, author, date)
                rev_id += 1
            else:  # pragma: no cover - defensive
                raise ValueError(revision.kind)
    return rev_id


def apply_revision_plan(document: Any, plan: Any, old_document: Any, *, author: str, date: str | None) -> None:
    if (
        not plan.paragraphs
        and not getattr(plan, "table_rows", ())
        and not getattr(plan, "body_paragraphs", ())
        and not getattr(plan, "run_formats", ())
        and not getattr(plan, "paragraph_formats", ())
    ):
        return
    when = _revision_date(date)
    output_paragraphs = _paragraphs(document, plan.everywhere)
    old_paragraphs = _paragraphs(old_document, plan.everywhere)
    rev_id = _next_revision_id(document)

    # Apply formatting revisions first. Text-revision rebuilding deep-copies
    # the new run/paragraph properties, so rPrChange/pPrChange markers survive
    # later insert/delete/replace reconstruction without offset drift.
    rev_id = _apply_paragraph_format_revisions(
        output_paragraphs, old_paragraphs, getattr(plan, "paragraph_formats", ()),
        rev_id=rev_id, author=author, date=when,
    )
    rev_id = _apply_run_format_revisions(
        output_paragraphs, old_paragraphs, getattr(plan, "run_formats", ()),
        rev_id=rev_id, author=author, date=when,
    )

    # Text revisions are applied before deleted rows are materialized, so the
    # plan's new-document paragraph indices remain stable.
    for revision in plan.paragraphs:
        new_index = revision.paragraph_index
        old_index = getattr(revision, "source_paragraph_index", new_index)
        try:
            out_p = output_paragraphs[new_index]
            old_p = old_paragraphs[old_index]
        except IndexError as exc:
            raise DocumentUnsupportedError(
                "paragraph alignment changed while applying DOCX revisions",
                code="compare-structural-change-not-supported",
                context={
                    "new_paragraph_index": new_index,
                    "old_paragraph_index": old_index,
                    "format": "docx",
                },
            ) from exc
        _assert_plain_paragraph(out_p, new_index)
        _assert_plain_paragraph(old_p, old_index)

        ppr = next((deepcopy(c) for c in out_p._p if _local(c) == "pPr"), None)
        rebuilt: list[Any] = []
        if ppr is not None:
            rebuilt.append(ppr)

        for edit in revision.edits:
            if edit.tag == "equal":
                rebuilt.extend(_slice_runs(out_p, edit.new_start, edit.new_end))
            elif edit.tag == "insert":
                runs = _slice_runs(out_p, edit.new_start, edit.new_end)
                rebuilt.append(_revision_container("ins", runs, rev_id, author, when))
                rev_id += 1
            elif edit.tag == "delete":
                runs = _slice_runs(old_p, edit.old_start, edit.old_end, deleted=True)
                rebuilt.append(_revision_container("del", runs, rev_id, author, when))
                rev_id += 1
            elif edit.tag == "replace":
                deleted_runs = _slice_runs(old_p, edit.old_start, edit.old_end, deleted=True)
                rebuilt.append(_revision_container("del", deleted_runs, rev_id, author, when))
                rev_id += 1
                inserted_runs = _slice_runs(out_p, edit.new_start, edit.new_end)
                rebuilt.append(_revision_container("ins", inserted_runs, rev_id, author, when))
                rev_id += 1
            else:  # pragma: no cover - defensive
                raise ValueError(edit.tag)

        out_p._p[:] = rebuilt

    rev_id = _apply_body_paragraph_revisions(
        document,
        old_document,
        getattr(plan, "body_paragraphs", ()),
        rev_id=rev_id,
        author=author,
        date=when,
    )

    rev_id = _apply_table_row_revisions(
        document,
        old_document,
        getattr(plan, "table_rows", ()),
        rev_id=rev_id,
        author=author,
        date=when,
    )
    _enable_track_revisions(document)


__all__ = ["apply_revision_plan"]
