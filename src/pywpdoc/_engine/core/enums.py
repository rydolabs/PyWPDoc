from __future__ import annotations
from enum import IntEnum


class WD_CELL_VERTICAL_ALIGNMENT(IntEnum):
    TOP = 0
    CENTER = 1
    BOTTOM = 3


WD_ALIGN_VERTICAL = WD_CELL_VERTICAL_ALIGNMENT


class WD_ORIENTATION(IntEnum):
    PORTRAIT = 0
    LANDSCAPE = 1


WD_ORIENT = WD_ORIENTATION


class WD_STYLE_TYPE(IntEnum):
    PARAGRAPH = 1
    CHARACTER = 2
    TABLE = 3
    LIST = 4


__all__ = [
    "WD_CELL_VERTICAL_ALIGNMENT", "WD_ALIGN_VERTICAL",
    "WD_ORIENTATION", "WD_ORIENT", "WD_STYLE_TYPE",
]
