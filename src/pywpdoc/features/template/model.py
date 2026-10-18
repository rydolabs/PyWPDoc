"""Pure template syntax model objects.

These objects intentionally know nothing about document backends.  They carry
only logical-text offsets and the variable path parsed from a template tag.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VariableTag:
    """One ``{{ variable }}`` placeholder in a logical text stream."""

    key: str
    start: int
    end: int
    raw: str


__all__ = ["VariableTag"]
