"""DOCX paragraph/run wrappers.

The wrappers expose the backend's shared paragraph surface while delegating all
text-mutation policy to :mod:`pywpdoc._engine.docx.text`.
"""
from __future__ import annotations

from ..core.proxy import NativeProxy
from .text import replace_paragraph
from .styles import Style, Styles, _unwrap_style
from .fragments import iter_paragraph_text_fragments


def _element_signature(element, *, skip_local_names=()):
    """Return a stable, namespace-aware structural signature for OOXML props."""
    if element is None:
        return None
    skip = set(skip_local_names)
    def local(node):
        tag = getattr(node, "tag", "")
        text = str(tag)
        return text.rsplit("}", 1)[-1] if "}" in text else text.split(":")[-1]
    def walk(node):
        return (
            str(node.tag),
            tuple(sorted((str(k), str(v)) for k, v in node.attrib.items())),
            node.text,
            tuple(walk(child) for child in node if local(child) not in skip),
        )
    return walk(element)


def _paragraph_format_signature(native):
    ppr = native._p.pPr
    return _element_signature(ppr, skip_local_names={"pPrChange", "sectPr"})


def _paragraph_section_signature(native):
    ppr = native._p.pPr
    if ppr is None:
        return None
    sect = next((child for child in ppr if str(child.tag).endswith("}sectPr")), None)
    return _element_signature(sect)


def _run_format_spans(native):
    spans = []
    offset = 0
    for run in native.runs:
        text = run.text or ""
        if not text:
            continue
        start = offset
        offset += len(text)
        spans.append((start, offset, _element_signature(run._r.rPr, skip_local_names={"rPrChange"})))
    return tuple(spans)


class Run(NativeProxy):
    @property
    def revision_format_signature(self):
        return _element_signature(self.native._r.rPr, skip_local_names={"rPrChange"})

    @property
    def style(self):
        native = self.native.style
        if native is None:
            return None
        return Style(native, Styles(self.native.part.document.styles))

    @style.setter
    def style(self, value) -> None:
        self.native.style = _unwrap_style(value)


class Paragraph(NativeProxy):
    @property
    def revision_format_signature(self):
        return _paragraph_format_signature(self.native)

    @property
    def revision_section_signature(self):
        return _paragraph_section_signature(self.native)

    def revision_run_format_spans(self):
        return _run_format_spans(self.native)

    @property
    def structural_token(self):
        """Opaque stable node identity for structure-aware feature passes."""
        return self.native._p

    @property
    def style(self):
        native = self.native.style
        if native is None:
            return None
        return Style(native, Styles(self.native.part.document.styles))

    @style.setter
    def style(self, value) -> None:
        self.native.style = _unwrap_style(value)

    @property
    def runs(self) -> list[Run]:
        return [Run(run) for run in self.native.runs]

    def iter_text_fragments(self):
        """Yield backend-owned native text-node fragments in visible order."""
        yield from iter_paragraph_text_fragments(self.native)

    def add_run(self, text: str | None = None, style=None) -> Run:
        return Run(self.native.add_run(text, style=_unwrap_style(style)))

    def clear(self) -> "Paragraph":
        self.native.clear()
        return self

    def insert_paragraph_before(self, text: str | None = None, style=None) -> "Paragraph":
        return Paragraph(self.native.insert_paragraph_before(text, _unwrap_style(style)))

    def replace(self, search: str, replacement: str, count: int = -1) -> int:
        return replace_paragraph(self.native, search, replacement, count)


__all__ = ["Paragraph", "Run"]
