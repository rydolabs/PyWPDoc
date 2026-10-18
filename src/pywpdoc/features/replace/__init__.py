"""Structure-preserving high-level text replacement and preview."""
from .api import replace_text
from .preview import preview_replace, ReplacementPreviewMatch, ReplacementPreviewReport

__all__ = ["replace_text", "preview_replace", "ReplacementPreviewMatch", "ReplacementPreviewReport"]
