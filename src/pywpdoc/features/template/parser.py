"""Small, logicless template parser for PyWPDoc.

v1 deliberately supports variable tags only.  Control tags are detected and
rejected explicitly so future section/loop support can be added without
silently changing current behavior.
"""
from __future__ import annotations

import re
from typing import Iterator

from pywpdoc.core import DocumentValueError, DocumentUnsupportedError

from .model import VariableTag

_TAG_RE = re.compile(r"{{\s*(.*?)\s*}}", re.DOTALL)
_CONTROL_PREFIXES = ("#", "^", "/", ">", "!", "&", "=")


def iter_variable_tags(text: str) -> Iterator[VariableTag]:
    """Yield variable tags in source order.

    Supported syntax is ``{{name}}`` and dotted names such as
    ``{{customer.name}}``.  ``{{.}}`` addresses the current context.
    """
    for match in _TAG_RE.finditer(text):
        inner = match.group(1).strip()
        if not inner:
            raise DocumentValueError(
                "template variable name must not be empty",
                code="template-tag-empty",
            )
        if inner.startswith(_CONTROL_PREFIXES):
            raise DocumentUnsupportedError(
                f"template control tag is not supported in v1: {match.group(0)}",
                code="template-control-not-supported-v1",
                context={"tag": match.group(0), "content": inner},
            )
        if "{{" in inner or "}}" in inner:
            raise DocumentValueError(
                f"invalid nested template tag: {match.group(0)}",
                code="template-tag-invalid",
            )
        yield VariableTag(
            key=inner,
            start=match.start(),
            end=match.end(),
            raw=match.group(0),
        )


__all__ = ["iter_variable_tags"]
