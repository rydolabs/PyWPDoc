"""Backend-neutral context resolution for logicless templates."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Resolution:
    """Result of resolving one dotted template name."""

    found: bool
    value: Any = None


@dataclass(frozen=True)
class ContextStack:
    """Internal parent-aware template context stack.

    A dedicated type avoids changing the historical meaning of a tuple passed
    by a user as ordinary template data.
    """

    values: tuple[Any, ...]

    def push(self, value: Any) -> "ContextStack":
        return ContextStack(self.values + (value,))


def resolve_value(context: Any, key: str) -> Resolution:
    """Resolve a Mustache-style dotted name without invoking methods.

    Mapping keys are preferred.  Plain object attributes are supported as a
    convenience, but callable attributes are treated as missing rather than
    executed.  ``{{.}}`` resolves to the current context itself.
    """
    if key == ".":
        return Resolution(True, context)

    current = context
    for part in key.split("."):
        if not part:
            return Resolution(False)
        if isinstance(current, Mapping):
            if part not in current:
                return Resolution(False)
            current = current[part]
            continue
        try:
            value = getattr(current, part)
        except (AttributeError, TypeError):
            return Resolution(False)
        if callable(value):
            return Resolution(False)
        current = value
    return Resolution(True, current)


def resolve_template_value(context: Any, key: str) -> Resolution:
    """Resolve from an internal context stack or from ordinary root data."""
    if isinstance(context, ContextStack):
        if not context.values:
            return Resolution(False)
        if key == ".":
            return Resolution(True, context.values[-1])
        for item in reversed(context.values):
            resolved = resolve_value(item, key)
            if resolved.found:
                return resolved
        return Resolution(False)
    return resolve_value(context, key)


def stringify_value(value: Any) -> str:
    """Convert one resolved value to document text.

    PyWPDoc templates do not perform HTML escaping because the destination is a
    word-processing document, not markup.  ``None`` is rendered as empty text.
    """
    if value is None:
        return ""
    if value is True:
        return "True"
    if value is False:
        return "False"
    return str(value)


__all__ = [
    "Resolution", "ContextStack", "resolve_value", "resolve_template_value",
    "stringify_value",
]
