"""High-level logicless document-template feature."""
from __future__ import annotations

from typing import Any

from pywpdoc.core import DocumentValueError
from pywpdoc.core.text import iter_text_paragraphs

from .renderer import render_paragraph
from .structure.rows import render_table_rows


def render_template(
    document: Any,
    data: Any,
    *,
    everywhere: bool = True,
    missing: str = "keep",
    sections: bool = False,
    table_rows: bool = False,
) -> int:
    """Render template tags throughout a document.

    Variables (``{{name}}`` / dotted names / ``{{.}}``) are stable behavior.
    ``sections=True`` enables inline Mustache sections. ``table_rows=True``
    additionally treats a section that wraps an entire table row as a
    structure-preserving row repeat/condition. Structural rows require section
    semantics to be enabled explicitly.
    """
    if table_rows and not sections:
        raise DocumentValueError(
            "table row repetition requires sections=True",
            code="template-row-repeat-requires-sections",
        )

    # The strict policy must not apply edits to earlier paragraphs before a
    # missing value in a later paragraph is discovered. This read-only pass
    # intentionally precedes row cloning and all text mutations.
    if missing == "error":
        from .check import check_template
        report = check_template(
            document, data, everywhere=everywhere,
            sections=sections, table_rows=table_rows,
        )
        if report.issues:
            issue = report.issues[0]
            raise DocumentValueError(
                issue.message,
                code=issue.code,
                context={"paragraph_index": issue.paragraph_index, "key": issue.key},
            )

    changed = 0
    skip_tokens: set[Any] = set()
    if table_rows and everywhere:
        row_changed, skip_tokens = render_table_rows(
            document,
            data,
            everywhere=everywhere,
            missing=missing,
            sections=sections,
        )
        changed += row_changed

    for paragraph in iter_text_paragraphs(document, everywhere=everywhere):
        token = getattr(paragraph, "structural_token", None)
        if token is not None and token in skip_tokens:
            continue
        changed += render_paragraph(
            paragraph,
            data,
            missing=missing,
            sections=sections,
        )
    return changed


__all__ = ["render_template"]
