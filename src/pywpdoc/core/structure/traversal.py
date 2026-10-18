"""Backend-neutral structural traversal capability entry points."""
from __future__ import annotations

from typing import Any, Iterable


def _structural_backend(document: Any) -> Any:
    return getattr(document, "backend", document)


def iter_tables(document: Any, *, everywhere: bool = True) -> Iterable[Any]:
    """Yield tables through the selected backend's structural capability."""
    backend = _structural_backend(document)
    iterator = getattr(backend, "iter_tables", None)
    if not callable(iterator):
        if everywhere:
            raise TypeError("document backend does not provide table traversal capability")
        yield from getattr(backend, "tables", ())
        return
    yield from iterator(everywhere=everywhere)


__all__ = ["iter_tables"]
