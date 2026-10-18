"""Structure-preserving tracked comparison.

The feature owns document alignment/diff semantics only. Native revision markup
remains backend-owned through ``clone_for_compare`` and
``apply_revision_plan``.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

from pywpdoc.core import DocumentUnsupportedError, DocumentValueError
from pywpdoc.core.text import iter_text_paragraphs

from .model import (
    BodyParagraphRevision, ParagraphRevision, ParagraphFormatRevision, RevisionPlan,
    RunFormatRevision, TableRowRevision, TextEdit,
)


def _document(value: Any, cls: type) -> Any:
    if isinstance(value, (str, Path)):
        return cls.open(value)
    if hasattr(value, "backend") and hasattr(value, "format"):
        return value
    raise DocumentValueError(
        "new document must be a path or PyWPDoc Document",
        code="compare-new-document-invalid",
    )


def _aligned_pairs(old_texts: list[str], new_texts: list[str]) -> list[tuple[int, int]]:
    """Align paragraphs conservatively, rejecting structural insert/delete."""
    matcher = SequenceMatcher(a=old_texts, b=new_texts, autojunk=False)
    pairs: list[tuple[int, int]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        old_len = i2 - i1
        new_len = j2 - j1
        if tag in {"insert", "delete"} or (tag == "replace" and old_len != new_len):
            raise DocumentUnsupportedError(
                "paragraph insertion/deletion is not supported by tracked comparison",
                code="compare-structural-change-not-supported",
                context={"old_range": [i1, i2], "new_range": [j1, j2], "opcode": tag},
                suggestion="use table-row structural changes only, or keep other paragraph structure unchanged",
            )
        pairs.extend(zip(range(i1, i2), range(j1, j2)))
    if len(pairs) != len(old_texts) or len(pairs) != len(new_texts):
        raise DocumentUnsupportedError(
            "documents could not be aligned one paragraph at a time",
            code="compare-structural-change-not-supported",
        )
    pairs.sort()
    return pairs


def _paragraph_token(paragraph: Any) -> Any:
    token = getattr(paragraph, "structural_token", None)
    if token is None:
        raise DocumentUnsupportedError(
            "document backend does not expose stable paragraph identity",
            code="compare-backend-capability-missing",
        )
    return token


def _paragraph_index(paragraphs: list[Any]) -> dict[Any, int]:
    result: dict[Any, int] = {}
    for index, paragraph in enumerate(paragraphs):
        token = _paragraph_token(paragraph)
        if token in result:
            raise DocumentUnsupportedError(
                "paragraph traversal returned duplicate structural identity",
                code="compare-paragraph-identity-ambiguous",
                context={"paragraph_index": index},
            )
        result[token] = index
    return result


def _block_kind(block: Any) -> str:
    name = type(block).__name__.lower()
    if "paragraph" in name:
        return "paragraph"
    if "table" in name:
        return "table"
    raise DocumentUnsupportedError(
        "body block traversal exposed an unsupported block type",
        code="compare-body-block-unsupported",
        context={"block_type": type(block).__name__},
    )


def _body_blocks(document: Any) -> list[tuple[str, Any, int | None]]:
    iterator = getattr(document, "iter_inner_content", None)
    if not callable(iterator):
        raise DocumentUnsupportedError(
            "document backend does not expose body block traversal",
            code="compare-backend-capability-missing",
        )
    records: list[tuple[str, Any, int | None]] = []
    table_index = 0
    for block in iterator():
        kind = _block_kind(block)
        if kind == "table":
            records.append((kind, block, table_index))
            table_index += 1
        else:
            records.append((kind, block, None))
    return records


def _paragraph_substitution_cost(old_text: str, new_text: str) -> float:
    if old_text == new_text:
        return 0.0
    ratio = SequenceMatcher(a=old_text, b=new_text, autojunk=False).ratio()
    return 0.25 + (1.0 - ratio) * 1.25


def _align_body_blocks(
    old_blocks: list[tuple[str, Any, int | None]],
    new_blocks: list[tuple[str, Any, int | None]],
) -> list[tuple[str, int | None, int | None]]:
    """Align top-level body paragraphs while using tables as fixed anchors.

    Paragraph edits cost less than delete+insert, so a one-for-one rewrite is
    treated as an inline text revision. Stable neighboring paragraphs/tables
    pull true insertions and deletions out as structural paragraph revisions.
    Table insertion/deletion or reordering has infinite cost and therefore
    fails closed instead of being inferred as paragraph movement.
    """
    inf = 10**9
    m, n = len(old_blocks), len(new_blocks)
    dp = [[float(inf)] * (n + 1) for _ in range(m + 1)]
    action: list[list[str | None]] = [[None] * (n + 1) for _ in range(m + 1)]
    dp[m][n] = 0.0

    for i in range(m - 1, -1, -1):
        if old_blocks[i][0] == "paragraph" and dp[i + 1][n] < inf:
            dp[i][n] = 1.0 + dp[i + 1][n]
            action[i][n] = "delete"
    for j in range(n - 1, -1, -1):
        if new_blocks[j][0] == "paragraph" and dp[m][j + 1] < inf:
            dp[m][j] = 1.0 + dp[m][j + 1]
            action[m][j] = "insert"

    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            old_kind, old_block, old_table_index = old_blocks[i]
            new_kind, new_block, new_table_index = new_blocks[j]
            choices: list[tuple[float, int, str]] = []
            if old_kind == new_kind == "table" and old_table_index == new_table_index:
                choices.append((dp[i + 1][j + 1], 0, "pair"))
            elif old_kind == new_kind == "paragraph":
                cost = _paragraph_substitution_cost(
                    str(getattr(old_block, "text", "") or ""),
                    str(getattr(new_block, "text", "") or ""),
                )
                choices.append((cost + dp[i + 1][j + 1], 0, "pair"))
            if old_kind == "paragraph":
                choices.append((1.0 + dp[i + 1][j], 1, "delete"))
            if new_kind == "paragraph":
                choices.append((1.0 + dp[i][j + 1], 2, "insert"))
            finite = [item for item in choices if item[0] < inf]
            if finite:
                best = min(finite, key=lambda item: (round(item[0], 12), item[1]))
                dp[i][j] = best[0]
                action[i][j] = best[2]

    if dp[0][0] >= inf:
        raise DocumentUnsupportedError(
            "table insertion/deletion or reordering is not supported by tracked comparison",
            code="compare-table-structure-not-supported",
        )

    result: list[tuple[str, int | None, int | None]] = []
    i = j = 0
    while i < m or j < n:
        choice = action[i][j]
        if choice == "pair":
            result.append(("pair", i, j))
            i += 1
            j += 1
        elif choice == "delete":
            result.append(("delete", i, j))
            i += 1
        elif choice == "insert":
            result.append(("insert", i, j))
            j += 1
        else:  # pragma: no cover - defensive
            raise RuntimeError("body block alignment reconstruction failed")
    return result


def _body_paragraph_alignment(
    old: Any,
    new: Any,
    old_paragraphs: list[Any],
    new_paragraphs: list[Any],
) -> tuple[list[tuple[int, int]], tuple[BodyParagraphRevision, ...], set[int], set[int]]:
    old_blocks = _body_blocks(old)
    new_blocks = _body_blocks(new)
    actions = _align_body_blocks(old_blocks, new_blocks)
    old_index = _paragraph_index(old_paragraphs)
    new_index = _paragraph_index(new_paragraphs)
    pairs: list[tuple[int, int]] = []
    revisions: list[BodyParagraphRevision] = []
    old_body_indices: set[int] = set()
    new_body_indices: set[int] = set()

    for block_index, (kind, block, _table_index) in enumerate(old_blocks):
        if kind != "paragraph":
            continue
        token = _paragraph_token(block)
        if token not in old_index:
            raise DocumentUnsupportedError(
                "body paragraph is outside document text traversal",
                code="compare-paragraph-identity-ambiguous",
                context={"old_block_index": block_index},
            )
        old_body_indices.add(old_index[token])
    for block_index, (kind, block, _table_index) in enumerate(new_blocks):
        if kind != "paragraph":
            continue
        token = _paragraph_token(block)
        if token not in new_index:
            raise DocumentUnsupportedError(
                "body paragraph is outside document text traversal",
                code="compare-paragraph-identity-ambiguous",
                context={"new_block_index": block_index},
            )
        new_body_indices.add(new_index[token])

    for action_name, old_block_index, new_block_index in actions:
        if action_name == "pair":
            assert old_block_index is not None and new_block_index is not None
            old_kind, old_block, _ = old_blocks[old_block_index]
            new_kind, new_block, _ = new_blocks[new_block_index]
            if old_kind == new_kind == "paragraph":
                pairs.append((old_index[_paragraph_token(old_block)], new_index[_paragraph_token(new_block)]))
            continue
        if action_name == "insert":
            assert new_block_index is not None
            revisions.append(BodyParagraphRevision("insert", None, new_block_index))
            continue
        if action_name == "delete":
            assert old_block_index is not None and new_block_index is not None
            revisions.append(BodyParagraphRevision("delete", old_block_index, new_block_index))
            continue
        raise RuntimeError(action_name)  # pragma: no cover

    return pairs, tuple(revisions), old_body_indices, new_body_indices


def _row_paragraph_indices(row: Any, paragraph_index: dict[Any, int]) -> list[int]:
    indices: list[int] = []
    seen: set[int] = set()
    iterator = getattr(row, "iter_text_paragraphs", None)
    if not callable(iterator):
        raise DocumentUnsupportedError(
            "table row does not expose text paragraph traversal",
            code="compare-backend-capability-missing",
        )
    for paragraph in iterator():
        token = _paragraph_token(paragraph)
        if token not in paragraph_index:
            # DOCX vertical-merge continuation cells may contain a synthetic
            # empty paragraph that the document-wide traversal intentionally
            # suppresses in favor of the merge anchor. It carries no visible
            # text, so excluding it preserves the traversal contract. Any
            # non-empty unmapped paragraph remains unsafe/ambiguous.
            if str(getattr(paragraph, "text", "") or "") == "":
                continue
            raise DocumentUnsupportedError(
                "table row paragraph is outside the document text traversal",
                code="compare-paragraph-identity-ambiguous",
            )
        index = paragraph_index[token]
        if index not in seen:
            seen.add(index)
            indices.append(index)
    return indices


def _row_signature(row: Any) -> tuple[int, tuple[str, ...]]:
    physical_cells = list(getattr(row, "physical_cells", ()) or ())
    iterator = getattr(row, "iter_text_paragraphs", None)
    texts = tuple(str(getattr(p, "text", "") or "") for p in iterator()) if callable(iterator) else ()
    return len(physical_cells), texts




def _row_substitution_cost(old_signature: tuple[int, tuple[str, ...]], new_signature: tuple[int, tuple[str, ...]]) -> float:
    if old_signature == new_signature:
        return 0.0
    if old_signature[0] != new_signature[0]:
        return 3.0
    old_text = "\u241f".join(old_signature[1])
    new_text = "\u241f".join(new_signature[1])
    ratio = SequenceMatcher(a=old_text, b=new_text, autojunk=False).ratio()
    return 0.25 + (1.0 - ratio) * 1.25


def _align_rows(old_rows: list[Any], new_rows: list[Any]) -> list[tuple[str, int | None, int | None]]:
    """Minimum-cost row alignment that prefers edits over delete+insert.

    Exact rows cost 0, a same-shape modified row costs at most 1.5, and an
    insertion/deletion costs 1.  This lets stable neighboring rows pull a
    newly inserted row out as structural while still treating a wholly edited
    one-for-one row as a content modification.
    """
    old_sigs = [_row_signature(row) for row in old_rows]
    new_sigs = [_row_signature(row) for row in new_rows]
    m, n = len(old_rows), len(new_rows)
    dp = [[0.0] * (n + 1) for _ in range(m + 1)]
    action: list[list[str | None]] = [[None] * (n + 1) for _ in range(m + 1)]
    for i in range(m - 1, -1, -1):
        dp[i][n] = dp[i + 1][n] + 1.0
        action[i][n] = "delete"
    for j in range(n - 1, -1, -1):
        dp[m][j] = dp[m][j + 1] + 1.0
        action[m][j] = "insert"
    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            pair = _row_substitution_cost(old_sigs[i], new_sigs[j]) + dp[i + 1][j + 1]
            delete = 1.0 + dp[i + 1][j]
            insert_cost = 1.0 + dp[i][j + 1]
            # Stable deterministic tie-break: pair, then delete, then insert.
            choices = [(pair, 0, "pair"), (delete, 1, "delete"), (insert_cost, 2, "insert")]
            best = min(choices, key=lambda item: (round(item[0], 12), item[1]))
            dp[i][j] = best[0]
            action[i][j] = best[2]

    result: list[tuple[str, int | None, int | None]] = []
    i = j = 0
    while i < m or j < n:
        choice = action[i][j]
        if choice == "pair":
            result.append(("pair", i, j))
            i += 1
            j += 1
        elif choice == "delete":
            result.append(("delete", i, j))
            i += 1
        elif choice == "insert":
            result.append(("insert", i, j))
            j += 1
        else:  # pragma: no cover - defensive
            raise RuntimeError("row alignment reconstruction failed")
    return result


def _table_row_alignment(
    old: Any,
    new: Any,
    old_paragraphs: list[Any],
    new_paragraphs: list[Any],
) -> tuple[list[tuple[int, int]], tuple[TableRowRevision, ...], set[int], set[int]]:
    """Align top-level body table rows and identify row insert/delete revisions.

    Tables whose row structure is unchanged deliberately stay on the v0.29
    flat paragraph-alignment path.  That preserves the historical behavior for
    merged/complex tables and limits structural identity mapping to tables that
    actually need row insertion/deletion semantics.

    For a structurally changed table, paragraph pairs cover all paragraphs in
    aligned rows, including nested table paragraphs. Structural changes inside
    nested tables are not inferred independently; if they change paragraph
    shape/count, alignment fails closed.
    """
    old_tables = list(getattr(old, "tables", ()))
    new_tables = list(getattr(new, "tables", ()))
    if len(old_tables) != len(new_tables):
        raise DocumentUnsupportedError(
            "table insertion/deletion is not supported by tracked comparison",
            code="compare-table-structure-not-supported",
            context={"old_table_count": len(old_tables), "new_table_count": len(new_tables)},
        )

    old_index = _paragraph_index(old_paragraphs)
    new_index = _paragraph_index(new_paragraphs)
    paragraph_pairs: list[tuple[int, int]] = []
    row_revisions: list[TableRowRevision] = []
    old_table_paragraphs: set[int] = set()
    new_table_paragraphs: set[int] = set()

    for table_index, (old_table, new_table) in enumerate(zip(old_tables, new_tables)):
        old_rows = list(old_table.rows)
        new_rows = list(new_table.rows)
        if len(old_table.columns) != len(new_table.columns):
            raise DocumentUnsupportedError(
                "table column-count changes are not supported by tracked comparison",
                code="compare-table-structure-not-supported",
                context={
                    "table_index": table_index,
                    "old_columns": len(old_table.columns),
                    "new_columns": len(new_table.columns),
                },
            )

        actions = _align_rows(old_rows, new_rows)
        if all(action == "pair" for action, _, _ in actions):
            # Preserve v0.29 paragraph alignment exactly when no row-structure
            # operation is needed. This also avoids imposing row-token rules on
            # vertically merged tables that were previously text-comparable.
            continue

        if old.format == "hwpx":
            raise DocumentUnsupportedError(
                "HWPX table-row Track Changes has no verified native row anchor",
                code="compare-hwpx-table-row-track-unsupported",
                context={
                    "table_index": table_index,
                    "row_change_count": sum(1 for action, _, _ in actions if action != "pair"),
                    "verified_track_change_types": ["Insert", "Delete", "CharShape", "ParaShape"],
                    "public_insert_delete_marker_scope": "hp:t mixed content",
                    "verified_hp_tr_revision_anchor": False,
                },
                suggestion=(
                    "use DOCX for row-level tracked revisions, keep HWPX table row structure unchanged, "
                    "or create a Hancom-authored native row-change HWPX with the v0.40.0 probe before enabling this path"
                ),
            )

        old_row_paragraphs = [_row_paragraph_indices(row, old_index) for row in old_rows]
        new_row_paragraphs = [_row_paragraph_indices(row, new_index) for row in new_rows]
        for indices in old_row_paragraphs:
            old_table_paragraphs.update(indices)
        for indices in new_row_paragraphs:
            new_table_paragraphs.update(indices)

        for action, old_row_index, new_row_index in actions:
            if action == "insert":
                assert new_row_index is not None
                row_revisions.append(
                    TableRowRevision(table_index, "insert", None, new_row_index)
                )
                continue
            if action == "delete":
                assert old_row_index is not None and new_row_index is not None
                row_revisions.append(
                    TableRowRevision(table_index, "delete", old_row_index, new_row_index)
                )
                continue

            assert old_row_index is not None and new_row_index is not None
            old_indices = old_row_paragraphs[old_row_index]
            new_indices = new_row_paragraphs[new_row_index]
            if len(old_indices) != len(new_indices):
                raise DocumentUnsupportedError(
                    "aligned table rows changed their internal paragraph structure",
                    code="compare-table-row-content-structure-not-supported",
                    context={
                        "table_index": table_index,
                        "old_row_index": old_row_index,
                        "new_row_index": new_row_index,
                        "old_paragraph_count": len(old_indices),
                        "new_paragraph_count": len(new_indices),
                    },
                )
            paragraph_pairs.extend(zip(old_indices, new_indices))

    return paragraph_pairs, tuple(row_revisions), old_table_paragraphs, new_table_paragraphs


def _paragraph_pairs(
    old: Any,
    new: Any,
    *,
    everywhere: bool,
) -> tuple[
    list[Any], list[Any], list[tuple[int, int]],
    tuple[TableRowRevision, ...], tuple[BodyParagraphRevision, ...],
]:
    old_paragraphs = list(iter_text_paragraphs(old, everywhere=everywhere))
    new_paragraphs = list(iter_text_paragraphs(new, everywhere=everywhere))

    body_pairs, body_revisions, old_body_indices, new_body_indices = _body_paragraph_alignment(
        old, new, old_paragraphs, new_paragraphs,
    )
    if body_revisions:
        old_sections = list(getattr(old, "sections", ()))
        new_sections = list(getattr(new, "sections", ()))
        if len(old_sections) != 1 or len(new_sections) != 1:
            raise DocumentUnsupportedError(
                "paragraph insertion/deletion across multi-section documents is not supported yet",
                code="compare-paragraph-section-boundary-unsupported",
                context={
                    "old_section_count": len(old_sections),
                    "new_section_count": len(new_sections),
                },
            )

    if not everywhere:
        body_pairs.sort(key=lambda item: (item[1], item[0]))
        return old_paragraphs, new_paragraphs, body_pairs, (), body_revisions

    table_pairs, row_revisions, old_table_indices, new_table_indices = _table_row_alignment(
        old, new, old_paragraphs, new_paragraphs,
    )

    old_reserved = old_body_indices | old_table_indices
    new_reserved = new_body_indices | new_table_indices
    old_remaining = [i for i in range(len(old_paragraphs)) if i not in old_reserved]
    new_remaining = [i for i in range(len(new_paragraphs)) if i not in new_reserved]
    old_remaining_texts = [str(getattr(old_paragraphs[i], "text", "") or "") for i in old_remaining]
    new_remaining_texts = [str(getattr(new_paragraphs[i], "text", "") or "") for i in new_remaining]
    remaining_local_pairs = _aligned_pairs(old_remaining_texts, new_remaining_texts)
    remaining_pairs = [
        (old_remaining[old_i], new_remaining[new_i])
        for old_i, new_i in remaining_local_pairs
    ]

    pairs = body_pairs + table_pairs + remaining_pairs
    pairs.sort(key=lambda item: (item[1], item[0]))
    return old_paragraphs, new_paragraphs, pairs, row_revisions, body_revisions


def _format_signature(paragraph: Any) -> Any:
    return getattr(paragraph, "revision_format_signature", None)


def _section_signature(paragraph: Any) -> Any:
    return getattr(paragraph, "revision_section_signature", None)


def _run_format_spans(paragraph: Any) -> tuple[tuple[int, int, Any], ...]:
    method = getattr(paragraph, "revision_run_format_spans", None)
    if not callable(method):
        return ()
    return tuple(method())


def _span_at(spans: tuple[tuple[int, int, Any], ...], position: int):
    for start, end, signature in spans:
        if start <= position < end:
            return start, end, signature
    return None


def _format_revisions_for_pair(
    old_paragraph: Any, new_paragraph: Any,
    *, old_index: int, new_index: int, opcodes: list[tuple[str, int, int, int, int]],
) -> tuple[list[RunFormatRevision], ParagraphFormatRevision | None]:
    if _section_signature(old_paragraph) != _section_signature(new_paragraph):
        raise DocumentUnsupportedError(
            "section-property changes are not supported by tracked comparison",
            code="compare-section-format-change-unsupported",
            context={"old_paragraph_index": old_index, "new_paragraph_index": new_index},
        )

    paragraph_revision = None
    if _format_signature(old_paragraph) != _format_signature(new_paragraph):
        paragraph_revision = ParagraphFormatRevision(new_index, old_index)

    old_spans = _run_format_spans(old_paragraph)
    new_spans = _run_format_spans(new_paragraph)
    revisions: list[RunFormatRevision] = []
    for tag, i1, i2, j1, j2 in opcodes:
        if tag != "equal" or i1 == i2:
            continue
        old_pos, new_pos = i1, j1
        remaining = i2 - i1
        while remaining > 0:
            old_span = _span_at(old_spans, old_pos)
            new_span = _span_at(new_spans, new_pos)
            old_end = i2 if old_span is None else min(i2, old_span[1])
            new_end = j2 if new_span is None else min(j2, new_span[1])
            step = min(old_end - old_pos, new_end - new_pos, remaining)
            if step <= 0:
                # A zero-width gap in backend run exposure is unsafe to infer.
                raise DocumentUnsupportedError(
                    "text-to-run formatting map is ambiguous",
                    code="compare-format-map-failed",
                    context={"old_paragraph_index": old_index, "new_paragraph_index": new_index},
                )
            old_sig = None if old_span is None else old_span[2]
            new_sig = None if new_span is None else new_span[2]
            if old_sig != new_sig:
                revisions.append(RunFormatRevision(
                    paragraph_index=new_index, old_paragraph_index=old_index,
                    old_start=old_pos, old_end=old_pos + step,
                    new_start=new_pos, new_end=new_pos + step,
                ))
            old_pos += step
            new_pos += step
            remaining -= step
    return revisions, paragraph_revision


def _untracked_content_signature(document: Any) -> tuple[Any, ...]:
    """Snapshot the parts excluded by a body-only comparison.

    The resulting document is cloned from *new*. Differences in excluded
    stories must not sneak into that clone as untracked, already-accepted
    changes.  Do not compare native XML IDs across independently constructed
    documents; use readable contents, paragraph formatting, and table geometry.
    """
    body_tokens = {
        _paragraph_token(p)
        for p in iter_text_paragraphs(document, everywhere=False)
    }
    paragraphs = []
    for p in iter_text_paragraphs(document, everywhere=True):
        if _paragraph_token(p) in body_tokens:
            continue
        text = str(getattr(p, "text", "") or "")
        if not text:
            # HWPX section carrier paragraphs inherit common paragraph style
            # resources but have no displayed contents. Their semantic format
            # can change along with the selected body paragraph, while they
            # remain structurally identical carrier records.
            continue
        paragraphs.append((text, _format_signature(p), _run_format_spans(p)))

    table_shapes = []
    for table in document.backend.iter_tables(everywhere=True):
        rows = list(table.rows)
        shape = []
        for row in rows:
            cells = getattr(row, "physical_cells", None)
            if cells is None:
                cells = row.cells
            # Cell.text is a convenient paragraph summary while nested tables
            # and their text are independently included by recursive traversal.
            shape.append(tuple(str(getattr(c, "text", "") or "") for c in cells))
        table_shapes.append((len(rows), len(table.columns), tuple(shape)))
    backend_signature = getattr(document.backend, "excluded_native_signature", None)
    if not callable(backend_signature):
        raise DocumentUnsupportedError(
            "native table and image comparison safety checks unavailable",
            code="compare-backend-capability-missing",
        )
    return (tuple(paragraphs), tuple(table_shapes), backend_signature())


def build_revision_plan(old: Any, new: Any, *, everywhere: bool = True) -> RevisionPlan:
    if old.format != new.format:
        raise DocumentValueError(
            "tracked comparison requires documents of the same format",
            code="compare-format-mismatch",
            context={"old_format": old.format, "new_format": new.format},
        )

    old_paragraphs, new_paragraphs, pairs, table_rows, body_paragraphs = _paragraph_pairs(
        old, new, everywhere=everywhere,
    )

    revisions: list[ParagraphRevision] = []
    run_formats: list[RunFormatRevision] = []
    paragraph_formats: list[ParagraphFormatRevision] = []
    for old_index, new_index in pairs:
        before = str(getattr(old_paragraphs[old_index], "text", "") or "")
        after = str(getattr(new_paragraphs[new_index], "text", "") or "")
        opcodes = list(SequenceMatcher(a=before, b=after, autojunk=False).get_opcodes())
        pair_run_formats, paragraph_format = _format_revisions_for_pair(
            old_paragraphs[old_index], new_paragraphs[new_index],
            old_index=old_index, new_index=new_index, opcodes=opcodes,
        )
        run_formats.extend(pair_run_formats)
        if paragraph_format is not None:
            paragraph_formats.append(paragraph_format)

        if before != after:
            edits = tuple(
                TextEdit(tag, i1, i2, j1, j2)
                for tag, i1, i2, j1, j2 in opcodes
            )
            revisions.append(
                ParagraphRevision(
                    paragraph_index=new_index,
                    old_text=before,
                    new_text=after,
                    edits=edits,
                    old_paragraph_index=old_index,
                )
            )

    # Preserve the backend's specific rejection for inline objects inside
    # inserted/deleted body paragraphs. Otherwise the general image-difference
    # guard would mask compare-unsafe-inline-structure and hinder diagnostics.
    if not everywhere and old.format == "docx":
        deleted = [r.old_block_index for r in body_paragraphs if r.kind == "delete"]
        inserted = [r.new_block_index for r in body_paragraphs if r.kind == "insert"]
        if deleted:
            old.backend.assert_body_revision_paragraphs_safe(deleted)
        if inserted:
            new.backend.assert_body_revision_paragraphs_safe(inserted)

    if not everywhere and _untracked_content_signature(old) != _untracked_content_signature(new):
        raise DocumentUnsupportedError(
            "body-only comparison would include untracked table or story changes",
            code="compare-outside-scope-changes-unsupported",
            suggestion="use everywhere=True for tracked table content, or keep excluded stories identical",
        )

    return RevisionPlan(
        format=old.format, everywhere=everywhere, paragraphs=tuple(revisions),
        table_rows=table_rows, body_paragraphs=body_paragraphs,
        run_formats=tuple(run_formats), paragraph_formats=tuple(paragraph_formats),
    )


def compare_documents(
    old: Any,
    new: Any,
    *,
    author: str = "PyWPDoc",
    date: str | None = None,
    everywhere: bool = True,
):
    """Return a new copy of *new* containing tracked changes from *old*.

    Text edits and top-level body paragraph insertion/deletion are supported
    for DOCX and HWPX. Character/paragraph formatting revisions are currently
    native-editor verified for DOCX only. HWPX formatting changes fail closed
    until a Hancom-authored sample establishes the exact native encoding. DOCX
    additionally supports top-level body table-row insertion/deletion as true
    row revisions; HWPX row-structure changes remain fail-closed.
    """
    new_doc = _document(new, type(old))
    plan = build_revision_plan(old, new_doc, everywhere=everywhere)

    clone = getattr(new_doc.backend, "clone_for_compare", None)
    if not callable(clone):
        raise DocumentUnsupportedError(
            "document backend does not provide comparison cloning",
            code="compare-backend-capability-missing",
        )
    result_backend = clone()
    apply_plan = getattr(result_backend, "apply_revision_plan", None)
    if not callable(apply_plan):
        raise DocumentUnsupportedError(
            "document backend does not provide tracked revision writing",
            code="compare-backend-capability-missing",
        )
    apply_plan(
        plan,
        old.backend,
        author=str(author or "PyWPDoc"),
        date=date,
    )
    return type(old)(result_backend)


__all__ = ["build_revision_plan", "compare_documents"]
