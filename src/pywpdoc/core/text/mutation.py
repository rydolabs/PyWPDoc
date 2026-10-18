"""Backend-neutral mutation of logical paragraph text ranges.

The primitive knows only the writable ``.text`` surface exposed by
:class:`TextMap` fragments.  It preserves the first matched fragment's native
formatting/container and leaves surviving prefix/suffix content on their
original fragments.
"""
from __future__ import annotations

from typing import Any

from .map import TextMap


def _get_text(source: Any) -> str:
    value = getattr(source, "text", "")
    return "" if value is None else str(value)


def _set_text(source: Any, value: str) -> None:
    try:
        source.text = value
    except (AttributeError, TypeError) as exc:
        raise TypeError("text source does not provide writable text capability") from exc


def replace_text_range(text_map: TextMap, start: int, end: int, replacement: str) -> None:
    """Replace one safe logical ``[start, end)`` range in-place.

    Callers applying multiple replacements to one paragraph should process
    ranges in reverse order so offsets from the original :class:`TextMap`
    remain valid.
    """
    if text_map.crosses_unsafe_boundary(start, end):
        raise ValueError("replacement range crosses an unsafe text boundary")

    touched = text_map.sources_for(start, end)
    if not touched:
        raise ValueError("replacement range must contain visible text")

    first = touched[0]
    last = touched[-1]
    first_local = start - first.start
    last_local_end = end - last.start
    replacement = str(replacement)

    if first is last:
        current = _get_text(first.source)
        _set_text(
            first.source,
            current[:first_local] + replacement + current[last_local_end:],
        )
        return

    first_current = _get_text(first.source)
    last_current = _get_text(last.source)
    _set_text(first.source, first_current[:first_local] + replacement)
    for segment in touched[1:-1]:
        _set_text(segment.source, "")
    _set_text(last.source, last_current[last_local_end:])


__all__ = ["replace_text_range"]
