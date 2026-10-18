"""Low-level HWPX header/footer content policy.

Kept below the standalone HWPX backend so ``hwpx.story`` can remain a thin
object adapter.  No imports from ``common`` or ``docx`` are allowed here.
"""
from __future__ import annotations
from typing import Any


def paragraph_text(story: Any) -> str:
    """Return block paragraph text without leaking nested-table cell text."""
    texts: list[str] = []
    for item in story.iter_inner_content():
        if type(item).__name__ == "Paragraph":
            texts.append(item.text)
    return "\n".join(texts)



def enable_auto_story_height(story: Any) -> None:
    """Let Hancom size a rich header/footer story from its block content.

    ``hp:subList/@textHeight`` is the story text-area height.  A fixed value
    equal to the header/footer distance is only suitable for a simple single
    line story.  Once additional paragraphs, tables, fields, or runs are
    authored, keeping that fixed box can make content overflow into the body.
    HWPX ParaList containers use ``0`` for content-sized text areas, so rich
    authored stories switch to that native auto-size form.
    """
    sub = story._ensure_sublist()
    sub.set("textHeight", "0")

def normalize_story_table(table: Any) -> None:
    from ._hwpx_table import normalize_authored_table
    normalize_authored_table(table)
