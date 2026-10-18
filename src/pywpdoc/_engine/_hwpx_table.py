"""Native HWPX table authoring defaults shared by HWPX entry points only."""
from __future__ import annotations
from typing import Any


def normalize_authored_table(table: Any) -> None:
    """Apply the HWPX backend's authored-cell defaults to *table*."""
    from .core import defaults
    from .core.units import Mm
    from .model import local_name

    margin = next((c for c in table.element_model.children if local_name(c.tag) == "inMargin"), None)
    if margin is not None:
        margin.set("left", str(int(Mm(defaults.CELL_MARGIN_LEFT_MM))))
        margin.set("right", str(int(Mm(defaults.CELL_MARGIN_RIGHT_MM))))
        margin.set("top", str(int(Mm(defaults.CELL_MARGIN_TOP_MM))))
        margin.set("bottom", str(int(Mm(defaults.CELL_MARGIN_BOTTOM_MM))))
    for row in table.rows:
        for cell in row.physical_cells:
            cell.vertical_alignment = defaults.DEFAULT_CELL_VERTICAL_ALIGNMENT


def fit_nested_table(table: Any, cell: Any, cols: int) -> None:
    if cols <= 0:
        return
    from .authoring import distribute_size
    from .core import defaults
    from .core.units import Mm

    target = max(
        int(cell.width)
        - int(Mm(defaults.CELL_MARGIN_LEFT_MM))
        - int(Mm(defaults.CELL_MARGIN_RIGHT_MM)),
        0,
    )
    for index, width in enumerate(distribute_size(target, cols)):
        table.columns[index].width = width
