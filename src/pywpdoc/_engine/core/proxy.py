from __future__ import annotations
from typing import Any


class NativeProxy:
    """Tiny delegation helper used independently by backend adapters."""

    def __init__(self, native: Any):
        object.__setattr__(self, "native", native)

    def __getattr__(self, name: str):
        return getattr(self.native, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "native":
            object.__setattr__(self, name, value)
            return
        descriptor = getattr(type(self), name, None)
        if descriptor is not None and hasattr(descriptor, "__set__"):
            descriptor.__set__(self, value)
            return
        setattr(self.native, name, value)
