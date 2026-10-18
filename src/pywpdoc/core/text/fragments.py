"""Backend-neutral text-fragment abstraction.

A :class:`TextFragment` is smaller than a paragraph/run.  It represents one
writable visible text source plus the information needed to decide whether two
adjacent fragments may be treated as one logical text stream.

Backends may expose ``paragraph.iter_text_fragments()``.  The objects yielded
by that capability need only provide ``.text`` and may optionally expose
``source``, ``kind`` and ``safe_join_before`` attributes.  This keeps feature
modules independent from OOXML/HWPX details while allowing a backend to model
native text nodes more precisely than a run-level abstraction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Iterator


@dataclass(frozen=True)
class TextFragment:
    """One writable fragment in a paragraph logical-text stream.

    ``safe_join_before=False`` means there is an opaque/structural boundary
    immediately before this fragment.  Search/template logic must not treat a
    match crossing that boundary as contiguous visible text.
    """

    source: Any
    text: str
    kind: str = "text"
    safe_join_before: bool = True


def _as_fragment(item: Any) -> TextFragment:
    if isinstance(item, TextFragment):
        return item
    source = getattr(item, "source", item)
    value = getattr(item, "text", getattr(source, "text", ""))
    value = "" if value is None else str(value)
    return TextFragment(
        source=source,
        text=value,
        kind=str(getattr(item, "kind", "text")),
        safe_join_before=bool(getattr(item, "safe_join_before", True)),
    )


def iter_text_fragments(paragraph: Any) -> Iterator[TextFragment]:
    """Yield backend-neutral text fragments for *paragraph*.

    Backends can provide a finer-grained capability without changing any
    feature package.  The fallback preserves the v0.25/v0.26 run/hyperlink
    behavior for backends that do not yet need native-node granularity.
    """

    provider = getattr(paragraph, "iter_text_fragments", None)
    if callable(provider):
        for item in provider():
            fragment = _as_fragment(item)
            if fragment.text:
                yield fragment
        return

    iterator = getattr(paragraph, "iter_inner_content", None)
    if callable(iterator):
        items: Iterable[Any] = iterator()
    else:
        items = getattr(paragraph, "runs", ())

    for item in items:
        value = getattr(item, "text", "")
        value = "" if value is None else str(value)
        if value:
            yield TextFragment(source=item, text=value)


__all__ = ["TextFragment", "iter_text_fragments"]
