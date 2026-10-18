"""Backend-neutral comparison/revision plan objects."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextEdit:
    tag: str
    old_start: int
    old_end: int
    new_start: int
    new_end: int


@dataclass(frozen=True)
class ParagraphRevision:
    """Tracked text edits for one aligned paragraph pair.

    ``paragraph_index`` remains the output/new-document paragraph index for
    compatibility with the v0.29 plan shape.  ``old_paragraph_index`` is
    populated when structural alignment makes the old/new indices diverge.
    """

    paragraph_index: int
    old_text: str
    new_text: str
    edits: tuple[TextEdit, ...]
    old_paragraph_index: int | None = None

    @property
    def new_paragraph_index(self) -> int:
        return self.paragraph_index

    @property
    def source_paragraph_index(self) -> int:
        return self.paragraph_index if self.old_paragraph_index is None else self.old_paragraph_index


@dataclass(frozen=True)
class RunFormatRevision:
    """A character/run-format change over text that is unchanged.

    Offsets are expressed in the visible old/new paragraph text. The range is
    split at both old and new run boundaries by the planner, so each revision
    maps one old run-property state to one new run-property state.
    """

    paragraph_index: int
    old_paragraph_index: int
    old_start: int
    old_end: int
    new_start: int
    new_end: int


@dataclass(frozen=True)
class ParagraphFormatRevision:
    """A paragraph-property change for an aligned paragraph pair."""

    paragraph_index: int
    old_paragraph_index: int


@dataclass(frozen=True)
class BodyParagraphRevision:
    """A top-level body paragraph insertion/deletion.

    ``new_block_index`` is an index in the new document's top-level block
    sequence (paragraphs and tables). For ``insert`` it identifies the existing
    new paragraph. For ``delete`` it is the insertion anchor where a copy of
    the old paragraph must be materialized in the review document.
    """

    kind: str
    old_block_index: int | None
    new_block_index: int


@dataclass(frozen=True)
class TableRowRevision:
    """A structural table-row insertion/deletion.

    For ``insert`` revisions ``new_row_index`` names the existing row in the
    new document and ``old_row_index`` is ``None``.  For ``delete`` revisions
    ``old_row_index`` names the source row that must be materialized in the
    review copy while ``new_row_index`` is the insertion anchor in the new
    table (``len(new.rows)`` means append after the last new row).
    """

    table_index: int
    kind: str
    old_row_index: int | None
    new_row_index: int


@dataclass(frozen=True)
class RevisionPlan:
    format: str
    everywhere: bool
    paragraphs: tuple[ParagraphRevision, ...]
    table_rows: tuple[TableRowRevision, ...] = ()
    body_paragraphs: tuple[BodyParagraphRevision, ...] = ()
    run_formats: tuple[RunFormatRevision, ...] = ()
    paragraph_formats: tuple[ParagraphFormatRevision, ...] = ()

    @property
    def change_count(self) -> int:
        text_changes = sum(1 for p in self.paragraphs for e in p.edits if e.tag != "equal")
        return (
            text_changes + len(self.table_rows) + len(self.body_paragraphs)
            + len(self.run_formats) + len(self.paragraph_formats)
        )


__all__ = [
    "TextEdit",
    "ParagraphRevision",
    "RunFormatRevision",
    "ParagraphFormatRevision",
    "BodyParagraphRevision",
    "TableRowRevision",
    "RevisionPlan",
]
