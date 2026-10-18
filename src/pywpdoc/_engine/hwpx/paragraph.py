"""HWPX paragraph/run wrappers for the standalone backend."""
from __future__ import annotations

from ..core.proxy import NativeProxy
from .text import replace_paragraph
from .styles import Style, Styles, _unwrap_style


def _model_signature(node, *, ignore_id=False):
    if node is None:
        return None
    attrs = tuple((k, v) for k, v in node.attrs if not (ignore_id and k == "id"))
    return (
        node.tag, attrs, node.text, node.tail,
        tuple(_model_signature(child, ignore_id=False) for child in node.children),
    )


def _run_format_signature(native):
    document = getattr(native, "document", None)
    if document is None:
        return ("charPrIDRef", native.char_pr_id_ref)
    prop = document.styles.char_property(native.char_pr_id_ref)
    if prop is None:
        return ("missing-charPr", native.char_pr_id_ref)
    # Resource ids are header-local. Resolve them before comparing documents so
    # the same numeric font/border id cannot hide a cross-document format change.
    from .revisions import _resolved_char_property_signature
    return _resolved_char_property_signature(document, prop)


def _paragraph_format_signature(native):
    document = getattr(native, "document", None)
    if document is None:
        return (native.style_id_ref, native.para_pr_id_ref)
    prop = document.styles.paragraph_property(native.para_pr_id_ref)
    if prop is None:
        return (native.style_id_ref, ("missing-paraPr", native.para_pr_id_ref))
    # Resolve both the named-style identity and paraPr dependency graph
    # semantically; all of their numeric ids are local to each HWPX header.
    from .revisions import _resolved_para_property_signature, _resolved_style_identity_signature
    return (
        _resolved_style_identity_signature(document, native.style_id_ref or "0"),
        _resolved_para_property_signature(document, prop),
    )


def _run_format_spans(native):
    spans = []
    offset = 0
    for run in native.runs:
        text = run.text or ""
        if not text:
            continue
        start = offset
        offset += len(text)
        spans.append((start, offset, _run_format_signature(run)))
    return tuple(spans)


class Run(NativeProxy):
    @property
    def revision_format_signature(self):
        return _run_format_signature(self.native)

    @property
    def style(self):
        native = self.native.style
        if native is None:
            return None
        return Style(native, Styles(self.native.document.styles))

    @style.setter
    def style(self, value) -> None:
        self.native.style = _unwrap_style(value)


class Paragraph(NativeProxy):
    @property
    def revision_format_signature(self):
        return _paragraph_format_signature(self.native)

    @property
    def revision_section_signature(self):
        # Section setup is carried by structural runs rather than paraPr.
        return None

    def revision_run_format_spans(self):
        return _run_format_spans(self.native)

    @property
    def structural_token(self):
        """Opaque stable node identity for structure-aware feature passes."""
        return id(self.native.element_model)

    @property
    def style(self):
        native = self.native.style
        if native is None:
            return None
        return Style(native, Styles(self.native.document.styles))

    @style.setter
    def style(self, value) -> None:
        self.native.style = _unwrap_style(value)

    @property
    def runs(self) -> list[Run]:
        return [Run(run) for run in self.native.runs]

    def add_run(self, text: str | None = None, style=None) -> Run:
        # The native HWPX expert API intentionally continues the previous
        # visible run's charPr when no explicit style/ref is supplied.  The
        # standalone DOCX-like backend contract is different: a newly added
        # run starts from the paragraph style, and direct formatting applied to
        # a previous sibling must not bleed into it.  Keep that normalization
        # here in the HWPX backend wrapper, not in common.
        if style is not None:
            return Run(self.native.add_run(text, style=_unwrap_style(style)))
        paragraph_style = self.native.style
        char_ref = paragraph_style.char_pr_id_ref if paragraph_style is not None else "0"
        return Run(self.native.add_run(text, char_pr_id_ref=char_ref or "0"))

    def clear(self) -> "Paragraph":
        self.native.clear()
        return self

    def insert_paragraph_before(self, text: str | None = None, style=None) -> "Paragraph":
        return Paragraph(self.native.insert_paragraph_before(text, _unwrap_style(style)))

    def replace(self, search: str, replacement: str, count: int = -1) -> int:
        return replace_paragraph(self.native, search, replacement, count)


__all__ = ["Paragraph", "Run"]
