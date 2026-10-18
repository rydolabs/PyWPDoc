"""Low-level HWPX section/story authoring policy.

This module belongs to the native HWPX engine, below the standalone ``hwpx``
backend wrappers.  It intentionally knows nothing about DOCX or the common
facade.
"""
from __future__ import annotations
from typing import Any



def invalidate_layout_cache(section: Any) -> int:
    """Drop stale paragraph line-layout caches for a section.

    Hancom persists ``hp:linesegarray`` as a derived layout cache.  Page size,
    margin, orientation, and header/footer-area changes can invalidate every
    cached line position in the section.  Keeping those coordinates after a
    geometry mutation can make Hancom lay out visible content against the old
    page box, so native geometry setters clear them instead of trying to patch
    opaque cached coordinates.
    """
    from .model import local_name

    removed = 0
    for node in section.element_model.iter():
        if local_name(node.tag) != "p":
            continue
        kept = []
        for child in node.children:
            if local_name(child.tag).lower() == "linesegarray":
                removed += 1
            else:
                kept.append(child)
        if len(kept) != len(node.children):
            node.children[:] = kept
    return removed

def content_width(section: Any) -> int:
    """Return the section's writable horizontal extent in HWPUNIT."""
    page = section.page_setup
    return max(int(page.width) - int(page.left_margin) - int(page.right_margin), 0)


def story_style_refs(section: Any, kind: str) -> tuple[str, str, str]:
    """Return native style/paragraph/character refs for a story's first line.

    The bundled Hancom skeleton has a dedicated ``Header``/``머리말`` style
    but no independent Footer style.  Hancom uses the story-specific style as
    the best native baseline for authored header/footer text; later paragraphs
    added explicitly keep ordinary paragraph defaults unless a style is given.
    """
    document = section.document
    if document is not None:
        style = document.styles.get("Header") or document.styles.get("머리말")
        if style is not None:
            return (str(style.id), str(style.para_pr_id_ref or "0"), str(style.char_pr_id_ref or "0"))
    return ("0", "0", "0")


def story_sublist_attrs(section: Any, kind: str) -> list[tuple[str, str]]:
    from .authoring import sublist_attrs

    attrs = dict(sublist_attrs())
    attrs["vertAlign"] = "TOP" if kind == "header" else "BOTTOM"
    attrs["textWidth"] = str(content_width(section))
    page = section.page_setup
    attrs["textHeight"] = str(int(page.header_distance if kind == "header" else page.footer_distance))
    return list(attrs.items())


def simple_story(section: Any, kind: str, page_type: str, text: str):
    from .authoring import object_id, paragraph_attrs
    from .model import ElementModel, HP

    style_ref, para_ref, char_ref = story_style_refs(section, kind)
    story = ElementModel(HP + kind, attrs=[("id", object_id()), ("applyPageType", page_type)])
    sub = ElementModel(HP + "subList", attrs=story_sublist_attrs(section, kind))
    if "\n" in text:
        sub.set("textHeight", "0")
    p = ElementModel(HP + "p", attrs=paragraph_attrs(para_pr_id_ref=para_ref, style_id_ref=style_ref))
    run = ElementModel(HP + "run", attrs=[("charPrIDRef", char_ref)])
    run.children.append(ElementModel(HP + "t", text=text))
    p.children.append(run)
    sub.children.append(p)
    story.children.append(sub)
    return story
