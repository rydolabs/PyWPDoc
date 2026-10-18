"""Standalone DOCX table object wrappers and creation operations."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterator

from ..core.proxy import NativeProxy
from ..core.enums import WD_ALIGN_VERTICAL
from ..core.errors import DocumentUnsupportedError, DocumentValueError
from ..core.units import Mm
from .paragraph import Paragraph
from .table_geometry import body_width, configure_table, fit_nested_table, set_table_width


def _to_core_length(value):
    if value is None:
        return None
    return Mm(value.mm) if hasattr(value, "mm") else value


def _to_native_length(value):
    if value is None:
        return None
    if hasattr(value, "mm"):
        try:
            from docx.shared import Mm as DocxMm
        except ImportError as exc:  # pragma: no cover
            raise ImportError("DOCX support requires the optional dependency 'python-docx>=1.2,<2'") from exc
        return DocxMm(float(value.mm))
    return value


def _vertical_enum():
    try:
        from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
    except ImportError as exc:  # pragma: no cover
        raise ImportError("DOCX support requires the optional dependency 'python-docx>=1.2,<2'") from exc
    return WD_CELL_VERTICAL_ALIGNMENT


def _docx_table_types():
    try:
        from docx.table import _Cell
        from docx.oxml.ns import qn
    except ImportError as exc:  # pragma: no cover
        raise ImportError("DOCX support requires the optional dependency 'python-docx>=1.2,<2'") from exc
    return _Cell, qn


@dataclass(frozen=True)
class _RowClone:
    """Opaque detached DOCX row snapshot used by the structural capability."""

    tr: Any
    part: Any


def _iter_cell_text_paragraphs(cell: "Cell") -> Iterator[Paragraph]:
    yield from cell.paragraphs
    for table in cell.tables:
        for row in table.rows:
            yield from row.iter_text_paragraphs()


def _assert_clone_safe(tr: Any) -> None:
    """Reject structures whose identity/merge semantics cannot be cloned safely."""
    _, qn = _docx_table_types()
    if list(tr.iterdescendants(qn("w:vMerge"))):
        raise DocumentUnsupportedError(
            "row cloning across vertical merges is not supported",
            code="table-row-vertical-merge-unsupported",
        )
    unsafe = (
        "w:bookmarkStart", "w:bookmarkEnd", "w:commentRangeStart",
        "w:commentRangeEnd", "w:commentReference", "w:fldChar", "w:sdt",
    )
    for tag in unsafe:
        if list(tr.iterdescendants(qn(tag))):
            raise DocumentUnsupportedError(
                "row contains an inline/control structure that cannot be cloned safely",
                code="table-row-clone-unsafe-structure",
                context={"element": tag},
            )


def _refresh_drawing_ids(tr: Any, part: Any) -> None:
    """Assign fresh Word drawing ids while retaining the same media relations."""
    _, qn = _docx_table_types()
    nodes = list(tr.iterdescendants(qn("wp:docPr")))
    if not nodes:
        return
    next_id = int(part.next_id)
    for offset, node in enumerate(nodes):
        node.set("id", str(next_id + offset))


def _row_has_vertical_merge(tr: Any) -> bool:
    _, qn = _docx_table_types()
    return bool(list(tr.iterdescendants(qn("w:vMerge"))))


def _insert_boundary_crosses_vertical_merge(rows: Any, index: int) -> bool:
    """True when *index* sits between a vMerge restart and continuation."""
    if index <= 0 or index >= len(rows):
        return False
    _, qn = _docx_table_types()
    for node in rows[index]._tr.iterdescendants(qn("w:vMerge")):
        value = node.get(qn("w:val"))
        if value is None or str(value).lower() != "restart":
            return True
    return False


class Cell(NativeProxy):
    @property
    def vertical_alignment(self):
        value = self.native.vertical_alignment
        if value is None:
            return WD_ALIGN_VERTICAL.TOP
        return WD_ALIGN_VERTICAL(int(value))

    @vertical_alignment.setter
    def vertical_alignment(self, value) -> None:
        native_enum = _vertical_enum()
        try:
            common = value if isinstance(value, WD_ALIGN_VERTICAL) else WD_ALIGN_VERTICAL(int(value))
        except (TypeError, ValueError) as exc:
            raise DocumentValueError(
                "cell vertical_alignment must be TOP, CENTER, or BOTTOM",
                code="cell-vertical-alignment-invalid",
                context={"requested": repr(value)},
            ) from exc
        self.native.vertical_alignment = native_enum(int(common))

    @property
    def width(self):
        return _to_core_length(self.native.width)

    @width.setter
    def width(self, value) -> None:
        self.native.width = _to_native_length(value)

    @property
    def paragraphs(self) -> list[Paragraph]:
        return [Paragraph(p) for p in self.native.paragraphs]

    @property
    def tables(self) -> list["Table"]:
        return [Table(t) for t in self.native.tables]

    def add_table(self, rows: int, cols: int, style=None) -> "Table":
        table = self.native.add_table(rows, cols)
        if style is not None:
            table.style = style
        configure_table(table)
        fit_nested_table(table, self.native, cols)
        return Table(table)

    def merge(self, other: "Cell") -> "Cell":
        return Cell(self.native.merge(other.native))


class Row(NativeProxy):
    @property
    def cells(self) -> list[Cell]:
        return [Cell(cell) for cell in self.native.cells]

    @property
    def physical_cells(self) -> list[Cell]:
        """Physical cells only; horizontally merged logical repeats are excluded."""
        _Cell, _ = _docx_table_types()
        return [Cell(_Cell(tc, self.native._parent)) for tc in self.native._tr.tc_lst]

    @property
    def height(self):
        return _to_core_length(self.native.height)

    @height.setter
    def height(self, value) -> None:
        self.native.height = _to_native_length(value)

    def iter_text_paragraphs(self) -> Iterator[Paragraph]:
        for cell in self.physical_cells:
            yield from _iter_cell_text_paragraphs(cell)

    def __iter__(self):
        return iter(self.cells)

    def __len__(self) -> int:
        return len(self.native.cells)

    def __getitem__(self, index):
        return self.cells[index]


class Column(NativeProxy):
    @property
    def cells(self) -> list[Cell]:
        return [Cell(cell) for cell in self.native.cells]

    @property
    def width(self):
        return _to_core_length(self.native.width)

    @width.setter
    def width(self, value) -> None:
        native_value = _to_native_length(value)
        self.native.width = native_value
        # python-docx's _Column.width updates tblGrid only. Our standalone
        # backend contract treats column width as the rendered cell width too,
        # so keep each tcW in sync inside this backend-owned module.
        for cell in self.native.cells:
            cell.width = native_value

    def __iter__(self):
        return iter(self.cells)

    def __len__(self) -> int:
        return len(self.cells)

    def __getitem__(self, index):
        return self.cells[index]


class Table(NativeProxy):
    @property
    def rows(self) -> list[Row]:
        return [Row(row) for row in self.native.rows]

    @property
    def columns(self) -> list[Column]:
        return [Column(column) for column in self.native.columns]

    def cell(self, row: int, col: int) -> Cell:
        return Cell(self.native.cell(row, col))

    def clone_row(self, index: int) -> object:
        """Return an opaque detached snapshot of one physical table row."""
        rows = self.native.rows
        if not 0 <= int(index) < len(rows):
            raise IndexError("row index out of range")
        tr = rows[int(index)]._tr
        _assert_clone_safe(tr)
        return _RowClone(deepcopy(tr), self.native.part)

    def insert_row(self, index: int, row_token: object) -> Row:
        """Insert a previously cloned row at *index* without flattening it."""
        rows = self.native.rows
        index = int(index)
        if not 0 <= index <= len(rows):
            raise IndexError("row insertion index out of range")
        if not isinstance(row_token, _RowClone) or row_token.part is not self.native.part:
            raise DocumentValueError(
                "row token was not created for this DOCX document part",
                code="table-row-token-invalid",
            )
        # Inserting a standalone row through an active vertical merge would
        # change the merge meaning. Keep the capability conservative.
        if _insert_boundary_crosses_vertical_merge(rows, index):
            raise DocumentUnsupportedError(
                "row insertion through a vertical merge is not supported",
                code="table-row-vertical-merge-unsupported",
            )

        tr = deepcopy(row_token.tr)
        _refresh_drawing_ids(tr, self.native.part)
        tbl = self.native._tbl
        if index < len(rows):
            rows[index]._tr.addprevious(tr)
        elif rows:
            rows[-1]._tr.addnext(tr)
        else:  # defensive: ordinary DOCX tables always have at least one row
            tbl.append(tr)
        return Row(self.native.rows[index])

    def remove_row(self, index: int) -> None:
        """Remove one row while refusing ambiguous vertical-merge mutation."""
        rows = self.native.rows
        index = int(index)
        if not 0 <= index < len(rows):
            raise IndexError("row index out of range")
        if len(rows) <= 1:
            raise DocumentValueError(
                "a table must keep at least one row",
                code="table-row-last-remove",
            )
        tr = rows[index]._tr
        if _row_has_vertical_merge(tr):
            raise DocumentUnsupportedError(
                "removing a row that participates in a vertical merge is not supported",
                code="table-row-vertical-merge-unsupported",
            )
        tr.getparent().remove(tr)


def create_document_table(document: Any, rows: int, cols: int, style=None) -> Table:
    """Create a top-level table using DOCX backend defaults only."""
    table = document.add_table(rows, cols)
    if style is not None:
        table.style = style
    set_table_width(table, body_width(document), cols)
    configure_table(table)
    return Table(table)
