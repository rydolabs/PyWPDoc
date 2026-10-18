"""Document-text renderer for logicless template tags.

The renderer depends only on shared logical-text map/mutation primitives.  It
has no knowledge of HWPX, DOCX, python-docx, or sibling feature packages.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from pywpdoc.core import DocumentValueError, DocumentUnsupportedError
from pywpdoc.core.text import TextMap, replace_text_range

from .context import ContextStack, resolve_template_value, stringify_value
from .model import VariableTag
from .parser import iter_variable_tags
from .structure import parse_section_blocks
from .sections import render_section_text

_MISSING_POLICIES = {"keep", "empty", "error"}


@dataclass(frozen=True)
class _Edit:
    start: int
    end: int
    replacement: str


def _validate_missing(missing: str) -> None:
    if missing not in _MISSING_POLICIES:
        raise DocumentValueError(
            f"invalid missing policy: {missing!r}",
            code="template-missing-policy-invalid",
            context={"missing": missing},
        )


def _outer_section_blocks(text: str) -> list[Any]:
    blocks = parse_section_blocks(text)
    outer: list[Any] = []
    for block in blocks:
        start = block.open_marker.start
        end = block.close_marker.end
        if any(
            parent.open_marker.start < start and end <= parent.close_marker.end
            for parent in blocks
        ):
            continue
        outer.append(block)
    return outer


def _iter_variables_outside_sections(text: str, outer: Iterable[Any]) -> Iterable[VariableTag]:
    """Yield variable tags only from source ranges not owned by sections.

    Rendering from the original source map prevents values produced by section
    expansion from being interpreted again as template syntax.
    """
    cursor = 0
    for block in outer:
        block_start = block.open_marker.start
        block_end = block.close_marker.end
        chunk = text[cursor:block_start]
        for tag in iter_variable_tags(chunk):
            yield VariableTag(
                key=tag.key,
                start=tag.start + cursor,
                end=tag.end + cursor,
                raw=tag.raw,
            )
        cursor = block_end
    chunk = text[cursor:]
    for tag in iter_variable_tags(chunk):
        yield VariableTag(
            key=tag.key,
            start=tag.start + cursor,
            end=tag.end + cursor,
            raw=tag.raw,
        )


def _variable_edit(text_map: TextMap, tag: VariableTag, data: Any, *, missing: str) -> _Edit | None:
    if text_map.crosses_unsafe_boundary(tag.start, tag.end):
        raise DocumentUnsupportedError(
            f"template tag crosses an unsafe document boundary: {tag.raw}",
            code="template-unsafe-text-boundary",
            context={"tag": tag.raw, "key": tag.key},
        )
    resolved = resolve_template_value(data, tag.key)
    if resolved.found:
        return _Edit(tag.start, tag.end, stringify_value(resolved.value))
    if missing == "keep":
        return None
    if missing == "empty":
        return _Edit(tag.start, tag.end, "")
    raise DocumentValueError(
        f"template value not found: {tag.key}",
        code="template-value-missing",
        context={"key": tag.key},
    )


def render_paragraph(
    paragraph: Any,
    data: Any,
    *,
    missing: str = "keep",
    sections: bool = False,
) -> int:
    """Render template tags in one paragraph and return the changed count."""
    _validate_missing(missing)

    text_map = TextMap.from_paragraph(paragraph)
    if "{{" not in text_map.text:
        return 0

    edits: list[_Edit] = []
    changed = 0

    if sections:
        outer = _outer_section_blocks(text_map.text)
        for block in outer:
            start = block.open_marker.start
            end = block.close_marker.end
            if text_map.crosses_unsafe_boundary(start, end):
                raise DocumentUnsupportedError(
                    f"template section crosses an unsafe document boundary: {block.open_marker.raw}",
                    code="template-unsafe-text-boundary",
                    context={"tag": block.open_marker.raw, "key": block.key},
                )
            rendered = render_section_text(
                text_map.text[start:end],
                data,
                missing=missing,
            )
            edits.append(_Edit(start, end, rendered.text))
            changed += rendered.changed

        # Process only variables from the original text that are outside the
        # section-owned ranges.  This is intentionally a single source pass:
        # values containing ``{{...}}`` are data, not executable template text.
        variable_tags = _iter_variables_outside_sections(text_map.text, outer)
    else:
        variable_tags = iter_variable_tags(text_map.text)

    for tag in variable_tags:
        edit = _variable_edit(text_map, tag, data, missing=missing)
        if edit is not None:
            edits.append(edit)
            changed += 1

    for edit in sorted(edits, key=lambda item: item.start, reverse=True):
        replace_text_range(text_map, edit.start, edit.end, edit.replacement)
    return changed


__all__ = ["render_paragraph"]
