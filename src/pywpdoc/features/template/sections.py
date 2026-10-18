"""Pure Mustache-style section rendering for one logical text block.

The module is backend-neutral.  It renders ``{{#name}}`` and ``{{^name}}``
sections against a context stack and returns plain replacement text.  Document
mutation remains the responsibility of :mod:`pywpdoc.features.template.renderer`.

The renderer walks *source* template ranges once.  Rendered data is never fed
back into the parser, so values containing ``{{...}}`` stay data rather than
becoming recursively executable template syntax.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pywpdoc.core import DocumentValueError

from .context import ContextStack, Resolution, resolve_value, stringify_value
from .parser import iter_variable_tags
from .structure import SectionBlock, parse_section_blocks


@dataclass(frozen=True)
class SectionTextRender:
    """Rendered text plus the number of source constructs consumed."""

    text: str
    changed: int


def _resolve_stack(contexts: tuple[Any, ...], key: str) -> Resolution:
    if key == ".":
        return Resolution(True, contexts[-1])
    for context in reversed(contexts):
        resolved = resolve_value(context, key)
        if resolved.found:
            return resolved
    return Resolution(False)


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


def _top_level_blocks(blocks: list[SectionBlock]) -> list[SectionBlock]:
    result: list[SectionBlock] = []
    for block in blocks:
        start = block.open_marker.start
        end = block.close_marker.end
        if any(
            parent.open_marker.start < start and end <= parent.close_marker.end
            for parent in blocks
        ):
            continue
        result.append(block)
    return result


def _render_variables_source(
    text: str,
    contexts: tuple[Any, ...],
    *,
    missing: str,
) -> SectionTextRender:
    output: list[str] = []
    cursor = 0
    changed = 0
    for tag in iter_variable_tags(text):
        output.append(text[cursor:tag.start])
        resolved = _resolve_stack(contexts, tag.key)
        if resolved.found:
            output.append(stringify_value(resolved.value))
            changed += 1
        elif missing == "keep":
            output.append(tag.raw)
        elif missing == "empty":
            changed += 1
        else:
            raise DocumentValueError(
                f"template value not found: {tag.key}",
                code="template-value-missing",
                context={"key": tag.key},
            )
        cursor = tag.end
    output.append(text[cursor:])
    return SectionTextRender("".join(output), changed)


def _render_block(
    source: str,
    block: SectionBlock,
    contexts: tuple[Any, ...],
    *,
    missing: str,
) -> SectionTextRender:
    body = source[block.content_start:block.content_end]
    resolved = _resolve_stack(contexts, block.key)

    if block.kind.value == "inverted":
        if _truthy(resolved):
            return SectionTextRender("", 1)
        rendered = _render_source(body, contexts, missing=missing)
        return SectionTextRender(rendered.text, rendered.changed + 1)

    if not _truthy(resolved):
        return SectionTextRender("", 1)

    value = resolved.value
    if _is_sequence(value):
        pieces: list[str] = []
        changed = 1
        for item in value:
            rendered = _render_source(body, contexts + (item,), missing=missing)
            pieces.append(rendered.text)
            changed += rendered.changed
        return SectionTextRender("".join(pieces), changed)

    rendered = _render_source(body, contexts + (value,), missing=missing)
    return SectionTextRender(rendered.text, rendered.changed + 1)


def _render_source(
    text: str,
    contexts: tuple[Any, ...],
    *,
    missing: str,
) -> SectionTextRender:
    blocks = parse_section_blocks(text)
    outer = _top_level_blocks(blocks)
    if not outer:
        return _render_variables_source(text, contexts, missing=missing)

    output: list[str] = []
    cursor = 0
    changed = 0
    for block in outer:
        prefix = _render_variables_source(
            text[cursor:block.open_marker.start],
            contexts,
            missing=missing,
        )
        output.append(prefix.text)
        changed += prefix.changed

        rendered = _render_block(text, block, contexts, missing=missing)
        output.append(rendered.text)
        changed += rendered.changed
        cursor = block.close_marker.end

    suffix = _render_variables_source(text[cursor:], contexts, missing=missing)
    output.append(suffix.text)
    changed += suffix.changed
    return SectionTextRender("".join(output), changed)


def render_section_text(
    text: str,
    contexts: tuple[Any, ...] | Any,
    *,
    missing: str = "keep",
) -> SectionTextRender:
    """Render variables and balanced Mustache sections from source text once."""
    if isinstance(contexts, ContextStack):
        contexts = contexts.values
    elif not isinstance(contexts, tuple):
        contexts = (contexts,)
    if not contexts:
        contexts = (None,)
    return _render_source(text, contexts, missing=missing)


__all__ = ["SectionTextRender", "render_section_text"]
