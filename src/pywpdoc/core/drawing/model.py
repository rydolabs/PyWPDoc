"""Backend-neutral drawing layout model.

This module intentionally models *meaning*, not OOXML/HWPX serialization.
It is a small reusable contract for pictures, shapes, charts, text boxes, and
other drawing objects.  Backends remain responsible for mapping these values
to their native representation.

v0.26.0 keeps the model internal/experimental: no Document method consumes it
yet.  This lets the model be exercised by tests before it becomes public API.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from pywpdoc.core import DocumentValueError, Length, HwpUnit


class HorizontalRelativeTo(str, Enum):
    PAGE = "page"
    MARGIN = "margin"
    COLUMN = "column"
    CHARACTER = "character"
    LEFT_MARGIN = "left-margin"
    RIGHT_MARGIN = "right-margin"
    INSIDE_MARGIN = "inside-margin"
    OUTSIDE_MARGIN = "outside-margin"


class VerticalRelativeTo(str, Enum):
    PAGE = "page"
    MARGIN = "margin"
    PARAGRAPH = "paragraph"
    LINE = "line"
    TOP_MARGIN = "top-margin"
    BOTTOM_MARGIN = "bottom-margin"
    INSIDE_MARGIN = "inside-margin"
    OUTSIDE_MARGIN = "outside-margin"


class HorizontalAlign(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    INSIDE = "inside"
    OUTSIDE = "outside"


class VerticalAlign(str, Enum):
    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"
    INSIDE = "inside"
    OUTSIDE = "outside"


class WrapMode(str, Enum):
    NONE = "none"
    SQUARE = "square"
    TIGHT = "tight"
    THROUGH = "through"
    TOP_AND_BOTTOM = "top-and-bottom"


class WrapSide(str, Enum):
    BOTH = "both"
    LEFT = "left"
    RIGHT = "right"
    LARGEST = "largest"


def _length(value: Length | int | float | None) -> Length | None:
    if value is None or isinstance(value, Length):
        return value
    return HwpUnit(value)


@dataclass(frozen=True)
class HorizontalPosition:
    """Horizontal floating position relative to a document reference frame.

    Exactly one of ``offset`` and ``align`` may be supplied.  ``offset=None``
    and ``align=None`` is allowed while a backend-specific default is still
    being resolved.
    """

    relative_to: HorizontalRelativeTo = HorizontalRelativeTo.PAGE
    offset: Length | None = None
    align: HorizontalAlign | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "offset", _length(self.offset))
        if self.offset is not None and self.align is not None:
            raise DocumentValueError(
                "horizontal position cannot use both offset and align",
                code="drawing-position-conflict",
                context={"axis": "horizontal"},
            )


@dataclass(frozen=True)
class VerticalPosition:
    """Vertical floating position relative to a document reference frame."""

    relative_to: VerticalRelativeTo = VerticalRelativeTo.PARAGRAPH
    offset: Length | None = None
    align: VerticalAlign | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "offset", _length(self.offset))
        if self.offset is not None and self.align is not None:
            raise DocumentValueError(
                "vertical position cannot use both offset and align",
                code="drawing-position-conflict",
                context={"axis": "vertical"},
            )


@dataclass(frozen=True)
class WrapSpec:
    """Text wrapping semantics around a floating drawing."""

    mode: WrapMode = WrapMode.NONE
    side: WrapSide = WrapSide.BOTH
    distance_left: Length = field(default_factory=lambda: HwpUnit(0))
    distance_right: Length = field(default_factory=lambda: HwpUnit(0))
    distance_top: Length = field(default_factory=lambda: HwpUnit(0))
    distance_bottom: Length = field(default_factory=lambda: HwpUnit(0))

    def __post_init__(self) -> None:
        for name in (
            "distance_left", "distance_right", "distance_top", "distance_bottom"
        ):
            value = _length(getattr(self, name))
            if value is None or int(value) < 0:
                raise DocumentValueError(
                    "drawing wrap distance must be non-negative",
                    code="drawing-wrap-distance-invalid",
                    context={"field": name, "value": getattr(self, name)},
                )
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class CropSpec:
    """Normalized crop fractions measured inward from each edge (0..1)."""

    left: float = 0.0
    top: float = 0.0
    right: float = 0.0
    bottom: float = 0.0

    def __post_init__(self) -> None:
        for name in ("left", "top", "right", "bottom"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise DocumentValueError(
                    "drawing crop value must be between 0 and 1",
                    code="drawing-crop-invalid",
                    context={"field": name, "value": value},
                )
            object.__setattr__(self, name, value)
        if self.left + self.right >= 1.0 or self.top + self.bottom >= 1.0:
            raise DocumentValueError(
                "drawing crop cannot remove the entire image",
                code="drawing-crop-empty",
            )


@dataclass(frozen=True)
class DrawingTransform:
    """Transform semantics shared by pictures and future shapes/charts."""

    rotation_degrees: float = 0.0
    flip_horizontal: bool = False
    flip_vertical: bool = False
    crop: CropSpec | None = None

    def __post_init__(self) -> None:
        rotation = float(self.rotation_degrees) % 360.0
        object.__setattr__(self, "rotation_degrees", rotation)


@dataclass(frozen=True)
class InlinePlacement:
    """Drawing participates in the text flow as an inline character/object."""

    mode: str = field(default="inline", init=False)


@dataclass(frozen=True)
class FloatingPlacement:
    """Anchored/floating drawing placement independent from normal text flow."""

    horizontal: HorizontalPosition = field(default_factory=HorizontalPosition)
    vertical: VerticalPosition = field(default_factory=VerticalPosition)
    wrap: WrapSpec = field(default_factory=WrapSpec)
    behind_text: bool = False
    allow_overlap: bool = True
    layout_in_cell: bool = True
    lock_anchor: bool = False
    z_order: int = 0
    mode: str = field(default="floating", init=False)


DrawingPlacement = InlinePlacement | FloatingPlacement


@dataclass(frozen=True)
class DrawingLayout:
    """Reusable layout payload for a drawing-capable object."""

    placement: DrawingPlacement = field(default_factory=InlinePlacement)
    transform: DrawingTransform = field(default_factory=DrawingTransform)


__all__ = [
    "HorizontalRelativeTo", "VerticalRelativeTo",
    "HorizontalAlign", "VerticalAlign",
    "WrapMode", "WrapSide",
    "HorizontalPosition", "VerticalPosition", "WrapSpec",
    "CropSpec", "DrawingTransform",
    "InlinePlacement", "FloatingPlacement", "DrawingPlacement", "DrawingLayout",
]
