"""Standalone HWPX table object wrappers and creation operations."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterator

from ..core.proxy import NativeProxy
from ..core.units import Mm, HwpUnit
from ..core.errors import DocumentUnsupportedError, DocumentValueError
from ..model import Cell as NativeCell, ElementModel, local_name
from ..authoring import object_id, paragraph_id
from .paragraph import Paragraph
from .table_geometry import body_width, configure_table, fit_nested_table


@dataclass(frozen=True)
class _RowClone:
    """Opaque detached HWPX row snapshot used by the structural capability."""

    tr: ElementModel
    height: int
    document: Any


def _iter_cell_text_paragraphs(cell: "Cell") -> Iterator[Paragraph]:
    yield from cell.paragraphs
    for table in cell.tables:
        for row in table.rows:
            yield from row.iter_text_paragraphs()


def _remove_layout_caches(model: ElementModel) -> None:
    for node in model.iter():
        node.children[:] = [
            child for child in node.children if local_name(child.tag).lower() != "linesegarray"
        ]


def _refresh_clone_ids(model: ElementModel) -> None:
    """Refresh clone-local paragraph/object ids while preserving media refs."""
    for node in model.iter():
        name = local_name(node.tag)
        if name == "p" and node.get("id") not in (None, "", "0"):
            node.set("id", paragraph_id())
        if node.get("instid") is not None:
            ident = object_id()
            node.set("instid", ident)
            if node.get("id") is not None:
                node.set("id", ident)
        elif name == "tbl" and node.get("id") not in (None, ""):
            node.set("id", object_id())


def _assert_clone_safe(table: Any, index: int) -> None:
    coverage = table._coverage()
    for col in range(table.col_count):
        cell = coverage[(index, col)]
        row0, _ = cell.address
        row_span, _ = cell.span
        if row0 != index or row_span != 1:
            raise DocumentUnsupportedError(
                "row cloning across vertical merges is not supported",
                code="table-row-vertical-merge-unsupported",
            )
    unsafe = {
        "fieldBegin", "fieldEnd", "bookmark", "memo", "footNote", "endNote",
    }
    tr = table._tr_models()[index]
    for node in tr.iter():
        if local_name(node.tag) in unsafe:
            raise DocumentUnsupportedError(
                "row contains a control structure that cannot be cloned safely",
                code="table-row-clone-unsafe-structure",
                context={"element": local_name(node.tag)},
            )


def _assert_insert_boundary_safe(table: Any, index: int) -> None:
    for cell in table._all_cells():
        row0, _ = cell.address
        row_span, _ = cell.span
        if row0 < index < row0 + row_span:
            raise DocumentUnsupportedError(
                "row insertion through a vertical merge is not supported",
                code="table-row-vertical-merge-unsupported",
            )


class Cell(NativeProxy):
    @property
    def width(self):
        return HwpUnit(self.native.width)

    @width.setter
    def width(self, value) -> None:
        self.native.width = value

    @property
    def paragraphs(self) -> list[Paragraph]:
        return [Paragraph(p) for p in self.native.paragraphs]

    @property
    def tables(self) -> list["Table"]:
        return [Table(t) for t in self.native.tables]

    def add_table(self, rows: int, cols: int, style=None) -> "Table":
        table = self.native.add_table(rows, cols, style=style)
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
        return [Cell(cell) for cell in self.native.physical_cells]

    @property
    def height(self):
        return self.native.height

    @height.setter
    def height(self, value) -> None:
        self.native.height = value

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
        return self.native.width

    @width.setter
    def width(self, value) -> None:
        self.native.width = value

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
        """Return an opaque detached snapshot of one structural table row."""
        index = int(index)
        if not 0 <= index < self.native.row_count:
            raise IndexError("row index out of range")
        _assert_clone_safe(self.native, index)
        tr = ElementModel.from_dict(self.native._tr_models()[index].to_dict())
        _remove_layout_caches(tr)
        _refresh_clone_ids(tr)
        height = int(self.native._logical_row_heights()[index])
        return _RowClone(tr=tr, height=height, document=self.native.document)

    def insert_row(self, index: int, row_token: object) -> Row:
        """Insert a previously cloned row at *index* without flattening it."""
        index = int(index)
        row_count = self.native.row_count
        if not 0 <= index <= row_count:
            raise IndexError("row insertion index out of range")
        if not isinstance(row_token, _RowClone) or row_token.document is not self.native.document:
            raise DocumentValueError(
                "row token was not created for this HWPX document",
                code="table-row-token-invalid",
            )
        _assert_insert_boundary_safe(self.native, index)

        for cell in self.native._all_cells():
            row0, col0 = cell.address
            if row0 >= index:
                cell._set_address(row0 + 1, col0)

        tr = ElementModel.from_dict(row_token.tr.to_dict())
        _remove_layout_caches(tr)
        _refresh_clone_ids(tr)
        for child in tr.children:
            if local_name(child.tag) != "tc":
                continue
            cell = NativeCell(child, self.native.document)
            _old_row, col = cell.address
            cell._set_address(index, col)

        self.native._insert_tr_model(index, tr)
        self.native._model.set("rowCnt", str(row_count + 1))
        size = self.native._size_node()
        if size is not None:
            size.set("height", str(int(size.get("height", "0") or 0) + row_token.height))
        self.native._coverage()
        return Row(self.native.rows[index])

    def remove_row(self, index: int) -> None:
        """Remove one logical row using the native merge-aware implementation."""
        index = int(index)
        if not 0 <= index < self.native.row_count:
            raise IndexError("row index out of range")
        if self.native.row_count <= 1:
            raise DocumentValueError(
                "a table must keep at least one row",
                code="table-row-last-remove",
            )
        self.native.delete_row(index)


def create_document_table(document: Any, rows: int, cols: int, style=None) -> Table:
    """Create a top-level table using HWPX backend defaults only."""
    table = document.add_table(rows, cols, style=style, width=body_width(document))
    configure_table(table)
    return Table(table)
