"""HWPX-compatible exception names backed by the small core error module."""
from __future__ import annotations

from .core.errors import (
    DocumentError,
    DocumentValueError,
    DocumentStateError,
    DocumentUnsupportedError,
)

# Stable legacy names. Aliasing keeps ``except HwpxValueError`` compatible while
# allowing DOCX/common modules to depend only on backend-neutral core errors.
HwpxError = DocumentError
HwpxValueError = DocumentValueError
HwpxStateError = DocumentStateError
HwpxUnsupportedError = DocumentUnsupportedError


class HwpxValidationError(DocumentValueError):
    code = "validation-failed"

    def __init__(self, message: str, *, report=None):
        super().__init__(message, code=self.code)
        self.report = report

    def to_dict(self) -> dict:
        data = super().to_dict()
        if self.report is not None:
            data["report"] = self.report.to_dict()
        return data


__all__ = [
    "HwpxError", "HwpxValueError", "HwpxStateError", "HwpxUnsupportedError",
    "HwpxValidationError",
]
