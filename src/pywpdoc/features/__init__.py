"""Optional high-level feature modules.

Features grow horizontally and are side-effect free.  They depend on stable
core contracts/reusable primitives rather than concrete HWPX/DOCX backends.
"""
from .find import FindMatch, find
from .replace import replace_text
from .template import render_template
from .compare import build_revision_plan, compare_documents

__all__ = [
    "FindMatch", "find", "replace_text", "render_template",
    "build_revision_plan", "compare_documents",
]
