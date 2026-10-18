"""Read-only literal replacement preview using the exact replace matching primitive.

Offsets always refer to the original logical paragraph text (zero-based
Python string indices), not DOCX/HWPX XML positions. A preview makes no
promise about rendered page coordinates or writer availability.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any

from pywpdoc.core import DocumentValueError
from pywpdoc.core.text import TextMap, iter_text_map_literal_spans, iter_text_paragraphs


@dataclass(frozen=True)
class ReplacementPreviewMatch:
    """One candidate replacement; positions and context use the TextMap logical view."""

    paragraph_index: int
    start: int
    end: int
    before: str
    after: str
    logical_before: str
    logical_after: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReplacementPreviewReport:
    """Non-mutating snapshot of candidates that ``replace_text`` would match."""

    search: str
    replacement: str
    everywhere: bool
    case_sensitive: bool
    limit: int | None
    matches: tuple[ReplacementPreviewMatch, ...]

    @property
    def count(self) -> int:
        return len(self.matches)

    @property
    def has_matches(self) -> bool:
        return bool(self.matches)

    def to_dict(self) -> dict[str, Any]:
        return {
            "search": self.search,
            "replacement": self.replacement,
            "everywhere": self.everywhere,
            "case_sensitive": self.case_sensitive,
            "limit": self.limit,
            "count": self.count,
            "matches": [match.to_dict() for match in self.matches],
        }

    def to_json(self, *, indent: int | None = 2, ensure_ascii: bool = False) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii, indent=indent)


def preview_replace(
    document: Any, search: str, replacement: str, *,
    everywhere: bool = True, case_sensitive: bool = True, count: int = -1,
) -> ReplacementPreviewReport:
    """Preview literal replacements without editing the source document.

    Selection, traversal and limit handling mirror ``replace_text``. An
    opaque field/revision/control boundary cannot be crossed by one match.
    Results are snapshots: re-running after another edit may yield new offsets.
    ``logical_before`` and ``logical_after`` reflect TextMap visible text,
    which may omit native non-text elements such as tabs or drawings.
    """
    search = str(search)
    replacement = str(replacement)
    if not search:
        raise DocumentValueError("search must not be empty", code="replace-query-empty")

    # Intentionally share replace_text's count semantics, including None.
    limit = None if count is None or int(count) < 0 else int(count)
    found: list[ReplacementPreviewMatch] = []
    if limit == 0:
        return ReplacementPreviewReport(search, replacement, everywhere, case_sensitive, limit, ())

    for paragraph_index, paragraph in enumerate(iter_text_paragraphs(document, everywhere=everywhere)):
        if limit is not None and len(found) >= limit:
            break
        text_map = TextMap.from_paragraph(paragraph)
        if not text_map.text:
            continue
        remaining = -1 if limit is None else limit - len(found)
        spans = list(iter_text_map_literal_spans(
            text_map, search, case_sensitive=case_sensitive, count=remaining,
        ))
        if not spans:
            continue
        # All matches refer to the same original snapshot; right-to-left
        # assembly exactly reflects replace_text's reverse mutation order.
        result = text_map.text
        for span in reversed(spans):
            result = result[:span.start] + replacement + result[span.end:]
        for span in spans:
            found.append(ReplacementPreviewMatch(
                paragraph_index=paragraph_index,
                start=span.start,
                end=span.end,
                before=span.text,
                after=replacement,
                logical_before=text_map.text,
                logical_after=result,
            ))

    return ReplacementPreviewReport(
        search, replacement, everywhere, case_sensitive, limit, tuple(found),
    )


__all__ = ["preview_replace", "ReplacementPreviewMatch", "ReplacementPreviewReport"]
