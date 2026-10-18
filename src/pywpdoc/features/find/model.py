"""Public result types for the find feature."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FindMatch:
    """One literal text match inside a logical paragraph text stream."""

    paragraph: Any
    paragraph_index: int
    start: int
    end: int
    text: str


__all__ = ["FindMatch"]
