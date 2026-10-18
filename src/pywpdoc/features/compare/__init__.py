from .api import build_revision_plan, compare_documents
from .model import (
    TextEdit, ParagraphRevision, RunFormatRevision, ParagraphFormatRevision,
    TableRowRevision, RevisionPlan,
)

__all__ = [
    "build_revision_plan", "compare_documents",
    "TextEdit", "ParagraphRevision", "RunFormatRevision", "ParagraphFormatRevision",
    "TableRowRevision", "RevisionPlan",
]
