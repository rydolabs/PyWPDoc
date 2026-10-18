"""Backend-neutral entry point for text-bearing paragraph traversal."""
from __future__ import annotations

from typing import Any, Iterable


def _text_backend(document: Any) -> Any:
    """Return an object implementing the minimal text traversal capability."""
    return getattr(document, "backend", document)


def iter_text_paragraphs(document: Any, *, everywhere: bool = True) -> Iterable[Any]:
    """Yield text-bearing paragraphs through the backend capability boundary.

    ``everywhere=False`` means top-level body paragraphs only.  ``True`` uses
    the backend's preservation-aware traversal (tables/stories as supported by
    that backend) without exposing backend types to feature modules.
    """
    backend = _text_backend(document)
    iterator = getattr(backend, "iter_text_paragraphs", None)
    if not callable(iterator):
        if everywhere:
            raise TypeError("document backend does not provide text traversal capability")
        yield from getattr(backend, "paragraphs", ())
        return
    yield from iterator(everywhere=everywhere)


__all__ = ["iter_text_paragraphs"]
