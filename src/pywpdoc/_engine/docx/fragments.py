"""Preservation-aware DOCX text-fragment collection.

This module is backend-owned.  It translates WordprocessingML paragraph
content into a minimal sequence of writable text sources for high-level
features.  The public/core layers never import OOXML types.

The collector deliberately distinguishes *soft markers* (bookmarks/proofing
ranges/comments), which may be crossed by logical text, from *hard/opaque
boundaries* (fields, revisions, SDT, tabs/breaks/drawings/objects), which must
not be crossed by a template/search mutation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

from docx.oxml.ns import qn

_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
_W_FLD_CHAR_TYPE = qn("w:fldCharType")


def _local_name(element: Any) -> str:
    tag = getattr(element, "tag", "")
    return tag.rsplit("}", 1)[-1] if "}" in tag else str(tag)


@dataclass
class _TextNodeSource:
    """Writable OOXML ``w:t`` source with run/container provenance."""

    element: Any
    run_element: Any
    container_kind: str = "run"

    @property
    def text(self) -> str:
        return self.element.text or ""

    @text.setter
    def text(self, value: str) -> None:
        value = "" if value is None else str(value)
        self.element.text = value
        # Word requires xml:space="preserve" for significant leading/trailing
        # whitespace.  Keep the marker accurate after fragment-level mutation.
        if value[:1].isspace() or value[-1:].isspace():
            self.element.set(_XML_SPACE, "preserve")
        else:
            self.element.attrib.pop(_XML_SPACE, None)


@dataclass(frozen=True)
class _FragmentRecord:
    source: _TextNodeSource
    text: str
    kind: str = "docx-text"
    safe_join_before: bool = True


# Markers that carry range/annotation metadata but no visible text.  They do
# not interrupt a user's visible token such as ``{{customer.name}}``.
_SOFT_MARKERS = {
    "bookmarkStart", "bookmarkEnd",
    "proofErr",
    "commentRangeStart", "commentRangeEnd",
    "permStart", "permEnd",
}

# Containers whose text may be traversed safely for ordinary visible text.
# Hyperlinks are intentionally transparent; this also fixes the old run-level
# mutation problem where python-docx Hyperlink.text is not a writable source.
_TRANSPARENT_CONTAINERS = {"hyperlink", "smartTag", "customXml"}

# Containers/features that have document semantics beyond ordinary text.
# v0.27 fails closed around them instead of guessing how mutation should affect
# fields, revisions, content controls, or embedded objects.
_OPAQUE_CONTAINERS = {
    "sdt", "fldSimple",
    "ins", "del", "moveFrom", "moveTo",
    "oMath", "oMathPara",
}

# Run-level nodes that interrupt contiguous visible plain text for our current
# high-level mutation contract.
_RUN_BARRIERS = {
    "tab", "br", "cr", "drawing", "object", "pict", "sym",
    "separator", "continuationSeparator", "lastRenderedPageBreak",
    "noBreakHyphen", "softHyphen",
}


class _Collector:
    def __init__(self) -> None:
        self.pending_barrier = False
        self.field_depth = 0

    def barrier(self) -> None:
        self.pending_barrier = True

    def fragment(self, text_element: Any, run_element: Any, container_kind: str) -> _FragmentRecord | None:
        text = text_element.text or ""
        if not text:
            return None
        record = _FragmentRecord(
            source=_TextNodeSource(text_element, run_element, container_kind),
            text=text,
            safe_join_before=not self.pending_barrier,
        )
        self.pending_barrier = False
        return record

    def walk_run(self, run_element: Any, container_kind: str) -> Iterator[_FragmentRecord]:
        for child in run_element:
            name = _local_name(child)
            if name == "rPr":
                continue
            if name == "fldChar":
                fld_type = child.get(_W_FLD_CHAR_TYPE)
                self.barrier()
                if fld_type == "begin":
                    self.field_depth += 1
                elif fld_type == "end" and self.field_depth:
                    self.field_depth -= 1
                # "separate" and malformed field markers remain barriers.
                continue
            if name in {"instrText", "delText"}:
                self.barrier()
                continue
            if name == "t":
                if self.field_depth:
                    # Field result text is intentionally opaque for v0.27.
                    self.barrier()
                    continue
                record = self.fragment(child, run_element, container_kind)
                if record is not None:
                    yield record
                continue
            if name in _SOFT_MARKERS:
                continue
            # Any other run child either has visible non-text semantics or is
            # unknown to this collector; fail closed by creating a hard join
            # boundary before the next supported text node.
            self.barrier()

    def walk_container(self, element: Any, container_kind: str = "paragraph") -> Iterator[_FragmentRecord]:
        for child in element:
            name = _local_name(child)
            if name in {"pPr", "rPr"}:
                continue
            if name == "r":
                yield from self.walk_run(child, container_kind)
                continue
            if name in _SOFT_MARKERS:
                continue
            if name in _TRANSPARENT_CONTAINERS:
                yield from self.walk_container(child, name)
                continue
            if name in _OPAQUE_CONTAINERS:
                self.barrier()
                # Deliberately do not descend: text inside this semantic object
                # must not be mutated by the generic template engine yet.
                continue
            if name in _RUN_BARRIERS:
                self.barrier()
                continue
            # Unknown paragraph/container child: safest policy is an opaque
            # boundary rather than concatenating text across it silently.
            self.barrier()


def iter_paragraph_text_fragments(paragraph: Any) -> Iterator[_FragmentRecord]:
    """Yield preservation-aware writable text fragments for a python-docx paragraph."""
    collector = _Collector()
    yield from collector.walk_container(paragraph._p)


__all__ = ["iter_paragraph_text_fragments"]
