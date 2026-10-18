"""Thin HWPX table-geometry adapter over native HWPX authoring policy."""
from __future__ import annotations
from typing import Any

from .._hwpx_table import fit_nested_table as _fit_nested_table
from .._hwpx_table import normalize_authored_table


def body_width(document: Any) -> int:
    return int(document.sections[-1].content_width)


def configure_table(table: Any) -> None:
    normalize_authored_table(table)


def fit_nested_table(table: Any, cell: Any, cols: int) -> None:
    _fit_nested_table(table, cell, cols)
