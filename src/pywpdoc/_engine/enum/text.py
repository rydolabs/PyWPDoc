from __future__ import annotations

from enum import Enum, IntEnum


class WD_BREAK_TYPE(Enum):
    """Subset of python-docx break types that has a verified HWPX mapping."""

    LINE = "LINE"
    PAGE = "PAGE"
    COLUMN = "COLUMN"
    TEXT_WRAPPING = "LINE"


WD_BREAK = WD_BREAK_TYPE


class WD_TAB_ALIGNMENT(IntEnum):
    """Tab alignment values shared with the common python-docx subset."""

    LEFT = 0
    CENTER = 1
    RIGHT = 2
    DECIMAL = 3


class WD_TAB_LEADER(IntEnum):
    """python-docx-shaped tab leader values.

    HWPX has a slightly different leader vocabulary. The common four map
    directly enough for ordinary document authoring. HEAVY and MIDDLE_DOT are
    accepted as compatibility aliases and map to the closest HWPX rendering.
    """

    SPACES = 0
    DOTS = 1
    DASHES = 2
    LINES = 3
    HEAVY = 4
    MIDDLE_DOT = 5
