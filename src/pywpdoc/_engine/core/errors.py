from __future__ import annotations


class DocumentError(Exception):
    """Base error shared by backend-neutral API modules."""

    code = "document-error"

    def __init__(self, message: str, *, code: str | None = None, context: dict | None = None, suggestion: str | None = None):
        super().__init__(message)
        if code is not None:
            self.code = code
        self.context = dict(context or {})
        self.suggestion = suggestion

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": str(self),
            "context": dict(self.context),
            "suggestion": self.suggestion,
        }


class DocumentValueError(DocumentError, ValueError):
    code = "invalid-value"


class DocumentStateError(DocumentError, RuntimeError):
    code = "invalid-state"


class DocumentUnsupportedError(DocumentError, NotImplementedError):
    code = "unsupported-feature"


__all__ = [
    "DocumentError", "DocumentValueError", "DocumentStateError", "DocumentUnsupportedError"
]
