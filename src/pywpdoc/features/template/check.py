"""Read-only, backend-neutral preflight for PyWPDoc's existing template syntax.

This module deliberately does not call ``render_template`` or mutate document
XML.  It reports potentially destructive render attempts before the caller
opts into rendering.  Structural row-context handling shares the renderer's
row detection logic, but never clones or inserts rows.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from pywpdoc.core import DocumentValueError
from pywpdoc.core.structure import iter_tables
from pywpdoc.core.text import TextMap, iter_text_paragraphs

from .context import ContextStack, Resolution, resolve_template_value
from .structure import SectionKind, parse_section_blocks
from .structure.rows import _marker_records, _row_outer_section

_TAG = re.compile(r"{{(.*?)}}", re.DOTALL)
_CONTROL = (">", "!", "&", "=")


@dataclass(frozen=True)
class TemplateCheckIssue:
    """One preflight finding. Paragraph indices follow text traversal order."""

    code: str
    message: str
    paragraph_index: int
    key: str | None = None
    offset: int | None = None
    tag: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TemplateCheckReport:
    """Static source counts and resolution outcomes; never a render result."""

    tag_count: int
    checked_values: int
    resolved_values: int
    issues: tuple[TemplateCheckIssue, ...]

    @property
    def ok(self) -> bool:
        return not self.issues

    @property
    def missing_keys(self) -> tuple[str, ...]:
        return tuple(sorted({issue.key for issue in self.issues if issue.code == "template-value-missing" and issue.key is not None}))

    @property
    def missing_count(self) -> int:
        return sum(issue.code == "template-value-missing" for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "tag_count": self.tag_count,
            "checked_values": self.checked_values,
            "resolved_values": self.resolved_values,
            "missing_count": self.missing_count,
            "missing_keys": list(self.missing_keys),
            "issues": [issue.to_dict() for issue in self.issues],
        }


class _Checker:
    def __init__(self, sections: bool):
        self.sections = sections
        self.tag_count = 0
        self.checked_values = 0
        self.resolved_values = 0
        self.issues: list[TemplateCheckIssue] = []

    def issue(self, code: str, message: str, index: int, *, key: str | None = None,
              offset: int | None = None, tag: str | None = None) -> None:
        self.issues.append(TemplateCheckIssue(code, message, index, key, offset, tag))

    def validate(self, text: str, text_map: TextMap, index: int) -> bool:
        """Lexically validate all tags, including those in inactive sections."""
        invalid = False
        occupied = bytearray(len(text))
        for match in _TAG.finditer(text):
            occupied[match.start():match.end()] = b"\x01" * (match.end() - match.start())
            self.tag_count += 1
            raw, inner = match.group(), match.group(1).strip()
            code = None
            if not inner:
                code = "template-tag-empty"
            elif "{" in inner or "}" in inner:
                code = "template-tag-invalid"
            elif inner.startswith(("#", "^", "/")):
                if not self.sections:
                    code = "template-control-not-supported-v1"
                elif not inner[1:].strip():
                    code = "template-section-empty"
            elif inner.startswith(_CONTROL):
                code = "template-control-not-supported-v1"
            if code is not None:
                self.issue(code, f"unsupported or malformed template tag: {raw}", index,
                           tag=raw, offset=match.start())
                invalid = True
            if text_map.crosses_unsafe_boundary(match.start(), match.end()):
                self.issue("template-unsafe-text-boundary", "template tag crosses an unsafe text boundary",
                           index, tag=raw, offset=match.start())
                invalid = True

        # An unmatched delimiter is otherwise ignored by the render parser;
        # catching it before rendering is a deliberate, stricter preflight.
        for delimiter, code in (("{{", "template-tag-unclosed"), ("}}", "template-tag-orphan-close")):
            start = 0
            while True:
                pos = text.find(delimiter, start)
                if pos == -1:
                    break
                if not occupied[pos]:
                    self.issue(code, f"unmatched template delimiter {delimiter}", index, offset=pos)
                    invalid = True
                start = pos + 2

        if self.sections:
            try:
                blocks = parse_section_blocks(text)
            except DocumentValueError as exc:
                self.issue(exc.code, str(exc), index)
                invalid = True
            else:
                for block in blocks:
                    if text_map.crosses_unsafe_boundary(block.open_marker.start, block.close_marker.end):
                        self.issue("template-unsafe-text-boundary",
                                   "template section crosses an unsafe text boundary",
                                   index, key=block.key, offset=block.open_marker.start,
                                   tag=block.open_marker.raw)
                        invalid = True
        return not invalid

    def _variable_segment(self, text: str, contexts: ContextStack,
                          index: int, base: int) -> None:
        for match in _TAG.finditer(text):
            key = match.group(1).strip()
            self.checked_values += 1
            found = resolve_template_value(contexts, key).found
            if found:
                self.resolved_values += 1
            else:
                self.issue("template-value-missing", f"template value not found: {key}",
                           index, key=key, offset=base + match.start(), tag=match.group())

    @staticmethod
    def _truthy(resolved: Resolution) -> bool:
        if not resolved.found or resolved.value is None or resolved.value is False:
            return False
        value = resolved.value
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return len(value) > 0
        if isinstance(value, Mapping):
            return True
        return bool(value)

    def _evaluate(self, text: str, contexts: ContextStack, index: int, base: int = 0) -> None:
        if not self.sections:
            self._variable_segment(text, contexts, index, base)
            return
        blocks = parse_section_blocks(text)
        outer = [block for block in blocks if not any(
            parent.open_marker.start < block.open_marker.start
            and block.close_marker.end <= parent.close_marker.end for parent in blocks
        )]
        cursor = 0
        for block in outer:
            self._variable_segment(text[cursor:block.open_marker.start], contexts, index, base + cursor)
            resolved = resolve_template_value(contexts, block.key)
            truthy = self._truthy(resolved)
            content = text[block.content_start:block.content_end]
            if block.kind == SectionKind.INVERTED:
                if not truthy:
                    self._evaluate(content, contexts, index, base + block.content_start)
            elif truthy:
                value = resolved.value
                if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                    for item in value:
                        self._evaluate(content, contexts.push(item), index, base + block.content_start)
                else:
                    self._evaluate(content, contexts.push(value), index, base + block.content_start)
            cursor = block.close_marker.end
        self._variable_segment(text[cursor:], contexts, index, base + cursor)

    def paragraph(self, text_map: TextMap, index: int,
                  contexts: tuple[ContextStack, ...], *, override: str | None = None,
                  removed: tuple[tuple[int, int], ...] = ()) -> None:
        text = text_map.text if override is None else override
        virtual = text_map
        if override is not None:
            # Preserve native opaque boundaries after virtually removing the
            # structural row markers. No document nodes are edited.
            for start, end in removed:
                if text_map.crosses_unsafe_boundary(start, end):
                    self.issue("template-unsafe-text-boundary",
                               "structural row marker crosses an unsafe text boundary",
                               index, offset=start, tag=text_map.text[start:end])
            translated = []
            for boundary in text_map.unsafe_boundaries:
                if any(start < boundary < end for start, end in removed):
                    continue
                translated.append(boundary - sum(end - start for start, end in removed if end <= boundary))
            virtual = TextMap(text, (), tuple(translated))
        if not self.validate(text, virtual, index):
            return
        for context in contexts:
            self._evaluate(text, context, index)


def _row_contexts(document: Any, data: Any, checker: _Checker,
                  everywhere: bool) -> dict[Any, tuple[str, tuple[ContextStack, ...], tuple[tuple[int, int], ...]]]:
    """Plan row contexts without cloning a row or changing a table."""
    root = ContextStack((data,))
    by_token: dict[Any, tuple[str, tuple[ContextStack, ...], tuple[tuple[int, int], ...]]] = {}
    # Inner tables have precedence for nested structural repeat rows.
    for table in reversed(list(iter_tables(document, everywhere=everywhere))):
        for row in table.rows:
            try:
                outer = _row_outer_section(row)
            except DocumentValueError:
                # Per-paragraph syntax validation will also find the bad row.
                continue
            if outer is None:
                continue
            key, kind = outer
            resolved = resolve_template_value(root, key)
            truthy = checker._truthy(resolved)
            if kind == SectionKind.INVERTED:
                contexts = (root,) if not truthy else ()
            elif not truthy:
                contexts = ()
            elif isinstance(resolved.value, Sequence) and not isinstance(resolved.value, (str, bytes, bytearray)):
                contexts = tuple(root.push(item) for item in resolved.value)
            else:
                contexts = (root.push(resolved.value),)

            _, records = _marker_records(row)
            if not records:
                continue
            opener, closer = records[0], records[-1]
            checker.tag_count += 2  # source structural control markers
            nested_repeat = False
            for paragraph in row.iter_text_paragraphs():
                token = getattr(paragraph, "structural_token", None)
                if token in by_token:
                    # A nested row-repeat has a parent-dependent context, and
                    # independently resolving it against the root could give
                    # a dangerous false PASS. Report it for manual review.
                    nested_repeat = True
                    continue
                text = TextMap.from_paragraph(paragraph).text
                spans = [(m.marker.start, m.marker.end) for m in (opener, closer)
                         if getattr(m.paragraph, "structural_token", None) == token]
                for start, end in sorted(spans, reverse=True):
                    text = text[:start] + text[end:]
                by_token[token] = (text, contexts, tuple(spans))
            if nested_repeat:
                checker.issue(
                    "template-nested-row-context-unverified",
                    "nested structural row repetition needs a context-aware review",
                    -1, key=key,
                )
    return by_token


def check_template(document: Any, data: Any, *, everywhere: bool = True,
                   sections: bool = False, table_rows: bool = False) -> TemplateCheckReport:
    """Inspect source placeholders and their data without modifying the document.

    Missing *active* variables, malformed tags, unsupported syntax, and unsafe
    text boundaries are reported as issues.  Inactive conditional branches do
    not require data, as in ``render_template``. Structural row contexts are
    honored only when ``sections=True, table_rows=True``. A clean result is a
    preflight, not a guarantee of native application rendering correctness.
    """
    if table_rows and not sections:
        raise DocumentValueError("table row repetition requires sections=True",
                                 code="template-row-repeat-requires-sections")
    checker = _Checker(sections)
    contexts = ContextStack((data,))
    row_map = _row_contexts(document, data, checker, everywhere) if table_rows else {}
    for index, paragraph in enumerate(iter_text_paragraphs(document, everywhere=everywhere)):
        text_map = TextMap.from_paragraph(paragraph)
        token = getattr(paragraph, "structural_token", None)
        row = row_map.get(token)
        if row is None:
            checker.paragraph(text_map, index, (contexts,))
        else:
            override, row_contexts, spans = row
            checker.paragraph(text_map, index, row_contexts, override=override, removed=spans)
    return TemplateCheckReport(
        checker.tag_count, checker.checked_values, checker.resolved_values,
        tuple(checker.issues),
    )


__all__ = ["TemplateCheckIssue", "TemplateCheckReport", "check_template"]
