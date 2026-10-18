"""Experimental pure structural-template planning primitives."""
from .model import (
    SectionKind, SectionMarkerKind, SectionMarker, SectionBlock,
    TableRowRepeatPlan,
)
from .parser import iter_section_markers, parse_section_blocks

__all__ = [
    "SectionKind", "SectionMarkerKind", "SectionMarker", "SectionBlock",
    "TableRowRepeatPlan", "iter_section_markers", "parse_section_blocks",
]
