"""Conservative regex find/replace built on the shared logical TextMap.

Only nonempty matches inside one paragraph's safe logical text are supported.
No match may cross an opaque control/field/revision boundary. The replacement
plan is fully expanded before any mutation, avoiding partial writes from a
bad capture reference or a later zero-width match.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from pywpdoc.core import DocumentUnsupportedError, DocumentValueError
from pywpdoc.core.text import TextMap, iter_text_paragraphs, replace_text_range


@dataclass(frozen=True)
class RegexFindMatch:
    """Regex hit in a paragraph's logical text; offsets are zero-based."""

    paragraph: Any
    paragraph_index: int
    start: int
    end: int
    text: str
    groups: tuple[str | None, ...]
    groupdict: dict[str, str | None]


def _compile(pattern: str, flags: int) -> re.Pattern[str]:
    if not isinstance(pattern, str) or not pattern:
        raise DocumentValueError("pattern must be a nonempty string", code="regex-pattern-empty")
    try:
        compiled = re.compile(pattern, flags)
        # Reject patterns that admit the empty string even if count truncates
        # before the empty match at a later position.
        if compiled.search("") is not None:
            raise DocumentUnsupportedError(
                "zero-width regex matches are not supported",
                code="regex-zero-width",
            )
        return compiled
    except (re.error, ValueError, TypeError) as exc:
        raise DocumentValueError(
            f"invalid regular expression: {exc}", code="regex-pattern-invalid"
        ) from exc


def _gather(document: Any, regex: re.Pattern[str], *, everywhere: bool, count: int):
    """Read-only preflight; returns a global limit-sized replacement plan."""
    try:
        limit = None if count is None or int(count) < 0 else int(count)
    except (TypeError, ValueError, OverflowError) as exc:
        raise DocumentValueError("count must be an integer or None", code="regex-count-invalid") from exc
    if limit == 0:
        return []
    selected = []
    for index, paragraph in enumerate(iter_text_paragraphs(document, everywhere=everywhere)):
        if limit is not None and len(selected) >= limit:
            break
        text_map = TextMap.from_paragraph(paragraph)
        if not text_map.text:
            continue
        for match in regex.finditer(text_map.text):
            if match.start() == match.end():
                raise DocumentUnsupportedError(
                    "zero-width regex matches are not supported",
                    code="regex-zero-width",
                    context={"paragraph_index": index, "position": match.start()},
                )
            if not text_map.is_safe_range(match.start(), match.end()):
                continue  # exactly as in the existing literal find/replace
            selected.append((index, paragraph, text_map, match))
            if limit is not None and len(selected) >= limit:
                break
    return selected


def find_regex(
    document: Any, pattern: str, *, everywhere: bool = True,
    flags: int = 0, count: int = -1,
) -> list[RegexFindMatch]:
    """Find nonempty regex matches without crossing native text boundaries.

    Regex is applied separately to each logical paragraph, not across tables,
    paragraphs or native controls. Python ``re`` flags are supported.
    """
    regex = _compile(pattern, flags)
    return [
        RegexFindMatch(
            paragraph=paragraph, paragraph_index=index,
            start=match.start(), end=match.end(), text=match.group(0),
            groups=match.groups(), groupdict=match.groupdict(),
        )
        for index, paragraph, _map, match in _gather(
            document, regex, everywhere=everywhere, count=count,
        )
    ]


def replace_regex(
    document: Any, pattern: str, replacement: str, *,
    everywhere: bool = True, flags: int = 0, count: int = -1,
) -> int:
    """Replace safe regex matches, retaining the first matched run's styling.

    Supports Python ``Match.expand`` backreferences like ``\\1`` and
    ``\\g<name>``. Preflights ALL eligible matches and replacements before
    mutation. Unsafe matches are skipped and do not use the global limit.
    """
    if not isinstance(replacement, str):
        raise DocumentValueError("replacement must be a string", code="regex-replacement-invalid")
    regex = _compile(pattern, flags)
    matches = _gather(document, regex, everywhere=everywhere, count=count)
    plan = []
    for _index, _paragraph, text_map, match in matches:
        try:
            expanded = match.expand(replacement)
        except (re.error, IndexError, ValueError) as exc:
            raise DocumentValueError(
                f"invalid regex replacement: {exc}", code="regex-replacement-invalid"
            ) from exc
        plan.append((text_map, match.start(), match.end(), expanded))
    # Right-to-left within and across paragraphs: mapped offsets are from the
    # original snapshot, and no earlier matches are affected by later edits.
    for text_map, start, end, expanded in reversed(plan):
        replace_text_range(text_map, start, end, expanded)
    return len(plan)


__all__ = ["RegexFindMatch", "find_regex", "replace_regex"]
