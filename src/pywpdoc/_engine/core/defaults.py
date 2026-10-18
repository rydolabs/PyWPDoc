"""Shared *contract values*, not backend behavior.

Backends independently implement these defaults. The common facade never
performs geometry or format-specific normalization itself.
"""
PAGE_WIDTH_MM = 210.0
PAGE_HEIGHT_MM = 297.0
LEFT_MARGIN_MM = 30.0
RIGHT_MARGIN_MM = 30.0
TOP_MARGIN_MM = 20.0
BOTTOM_MARGIN_MM = 15.0
HEADER_DISTANCE_MM = 15.0
FOOTER_DISTANCE_MM = 15.0
CELL_MARGIN_LEFT_MM = 1.8
CELL_MARGIN_RIGHT_MM = 1.8
CELL_MARGIN_TOP_MM = 0.5
CELL_MARGIN_BOTTOM_MM = 0.5
DEFAULT_CELL_VERTICAL_ALIGNMENT = "TOP"
