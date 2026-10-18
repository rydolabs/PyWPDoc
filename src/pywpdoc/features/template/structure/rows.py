"""Backend-neutral structural table-row template rendering."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Iterable

from pywpdoc.core import DocumentUnsupportedError, DocumentValueError
from pywpdoc.core.structure import iter_tables
from pywpdoc.core.text import TextMap, replace_text_range

from ..context import ContextStack, Resolution, resolve_template_value
from ..renderer import render_paragraph
from .model import SectionKind, SectionMarkerKind, TableRowRepeatPlan
from .parser import iter_section_markers


@dataclass(frozen=True)
class _MarkerRecord:
    paragraph: Any
    paragraph_index: int
    marker: Any


def _direct_row_paragraphs(row: Any) -> list[Any]:
    paragraphs: list[Any] = []
    for cell in row.physical_cells:
        paragraphs.extend(cell.paragraphs)
    return paragraphs


def _marker_records(row: Any) -> tuple[list[Any], list[_MarkerRecord]]:
    paragraphs = _direct_row_paragraphs(row)
    records: list[_MarkerRecord] = []
    for p_index, paragraph in enumerate(paragraphs):
        for marker in iter_section_markers(paragraph.text):
            records.append(_MarkerRecord(paragraph, p_index, marker))
    return paragraphs, records


def _row_outer_section(row: Any) -> tuple[str, SectionKind] | None:
    """Return a row-spanning outer section, or ``None`` for ordinary inline use."""
    paragraphs, records = _marker_records(row)
    if not records:
        return None

    stack: list[_MarkerRecord] = []
    outer_open: _MarkerRecord | None = None
    outer_close: _MarkerRecord | None = None
    top_level_count = 0

    for record in records:
        marker = record.marker
        if marker.kind in (SectionMarkerKind.OPEN, SectionMarkerKind.INVERTED_OPEN):
            if not stack:
                top_level_count += 1
                if outer_open is None:
                    outer_open = record
            stack.append(record)
            continue
        if not stack:
            raise DocumentValueError(
                f"template section close without opener: {marker.raw}",
                code="template-section-unbalanced",
                context={"key": marker.key},
            )
        opener = stack.pop()
        if opener.marker.key != marker.key:
            raise DocumentValueError(
                f"template section mismatch: {opener.marker.key!r} closed by {marker.key!r}",
                code="template-section-mismatch",
                context={"open": opener.marker.key, "close": marker.key},
            )
        if not stack and outer_open is opener:
            outer_close = record

    if stack:
        opener = stack[-1].marker
        raise DocumentValueError(
            f"template section is not closed: {opener.raw}",
            code="template-section-unbalanced",
            context={"key": opener.key},
        )
    if top_level_count != 1 or outer_open is None or outer_close is None:
        return None

    # Structural row syntax is deliberately unambiguous: the outer section
    # must wrap all non-whitespace direct cell text in the row. Inline sections
    # that only wrap part of a cell remain handled by the ordinary renderer.
    for paragraph in paragraphs[:outer_open.paragraph_index]:
        if paragraph.text.strip():
            return None
    if outer_open.paragraph.text[:outer_open.marker.start].strip():
        return None
    if outer_close.paragraph.text[outer_close.marker.end:].strip():
        return None
    for paragraph in paragraphs[outer_close.paragraph_index + 1:]:
        if paragraph.text.strip():
            return None

    kind = (
        SectionKind.INVERTED
        if outer_open.marker.kind == SectionMarkerKind.INVERTED_OPEN
        else SectionKind.NORMAL
    )
    return outer_open.marker.key, kind


def build_table_row_repeat_plans(table: Any) -> list[TableRowRepeatPlan]:
    """Plan row-spanning section repeats without importing a concrete backend."""
    plans: list[TableRowRepeatPlan] = []
    for index, row in enumerate(table.rows):
        outer = _row_outer_section(row)
        if outer is None:
            continue
        key, kind = outer
        plans.append(
            TableRowRepeatPlan(
                key=key,
                row_token=table.clone_row(index),
                row_index=index,
                kind=kind,
            )
        )
    return plans


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _truthy(resolved: Resolution) -> bool:
    if not resolved.found:
        return False
    value = resolved.value
    if value is None or value is False:
        return False
    if _is_sequence(value):
        return len(value) > 0
    if isinstance(value, Mapping):
        return True
    return bool(value)


def _contexts_for_plan(plan: TableRowRepeatPlan, root: ContextStack) -> list[ContextStack]:
    resolved = resolve_template_value(root, plan.key)
    truthy = _truthy(resolved)
    if plan.kind == SectionKind.INVERTED:
        return [] if truthy else [root]
    if not truthy:
        return []
    value = resolved.value
    if _is_sequence(value):
        return [root.push(item) for item in value]
    return [root.push(value)]


def _strip_outer_markers(row: Any, key: str) -> None:
    paragraphs, records = _marker_records(row)
    del paragraphs
    if len(records) < 2:
        raise DocumentUnsupportedError(
            "cloned row lost its structural section markers",
            code="template-row-marker-lost",
            context={"key": key},
        )
    opener = records[0]
    closer = records[-1]
    if opener.marker.key != key or closer.marker.key != key:
        raise DocumentUnsupportedError(
            "cloned row structural marker mismatch",
            code="template-row-marker-lost",
            context={"key": key},
        )

    grouped: dict[Any, list[tuple[int, int]]] = {}
    for record in (opener, closer):
        grouped.setdefault(record.paragraph, []).append((record.marker.start, record.marker.end))

    for paragraph, ranges in grouped.items():
        text_map = TextMap.from_paragraph(paragraph)
        for start, end in sorted(ranges, reverse=True):
            if text_map.crosses_unsafe_boundary(start, end):
                raise DocumentUnsupportedError(
                    "table-row section marker crosses an unsafe document boundary",
                    code="template-unsafe-text-boundary",
                    context={"key": key},
                )
            replace_text_range(text_map, start, end, "")


def _render_inserted_row(
    row: Any,
    context: ContextStack,
    *,
    key: str,
    missing: str,
    sections: bool,
) -> tuple[int, set[Any]]:
    _strip_outer_markers(row, key)
    changed = 1  # outer structural section consumed
    tokens: set[Any] = set()
    for paragraph in row.iter_text_paragraphs():
        changed += render_paragraph(
            paragraph,
            context,
            missing=missing,
            sections=sections,
        )
        tokens.add(paragraph.structural_token)
    return changed, tokens


def render_table_rows(
    document: Any,
    data: Any,
    *,
    everywhere: bool = True,
    missing: str = "keep",
    sections: bool = True,
) -> tuple[int, set[Any]]:
    """Render row-spanning Mustache sections and return changed count + skip tokens.

    Tables are processed deepest-first so a nested table that already exists in
    the template is structurally settled before a containing row is cloned.
    """
    root = data if isinstance(data, ContextStack) else ContextStack((data,))
    changed = 0
    rendered_tokens: set[Any] = set()
    tables = list(iter_tables(document, everywhere=everywhere))

    for table in reversed(tables):
        plans = build_table_row_repeat_plans(table)
        planned = [(plan, _contexts_for_plan(plan, root)) for plan in plans]
        final_row_count = len(table.rows) + sum(len(contexts) for _, contexts in planned) - sum(
            1 for plan, _ in planned if plan.remove_template_row
        )
        if plans and final_row_count < 1:
            raise DocumentUnsupportedError(
                "table-row rendering would remove every row from the table",
                code="template-row-empty-table-unsupported",
            )
        for plan, contexts in sorted(
            planned, key=lambda item: int(item[0].row_index), reverse=True
        ):
            assert plan.row_index is not None
            insert_at = int(plan.row_index)
            for context in contexts:
                row = table.insert_row(insert_at, plan.row_token)
                row_changed, tokens = _render_inserted_row(
                    row,
                    context,
                    key=plan.key,
                    missing=missing,
                    sections=sections,
                )
                changed += row_changed
                rendered_tokens.update(tokens)
                insert_at += 1
            if plan.remove_template_row:
                table.remove_row(insert_at)
                if not contexts:
                    changed += 1

    return changed, rendered_tokens


__all__ = ["build_table_row_repeat_plans", "render_table_rows"]
