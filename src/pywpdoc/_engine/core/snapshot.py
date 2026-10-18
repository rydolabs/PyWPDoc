"""Backend-neutral document rebuild snapshot.

The common facade only transports this object.  Each backend owns the logic
that exports/imports it; no format XML or layout policy lives here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DocumentSnapshot:
    """Portable document description plus optional source-native payload.

    ``portable`` contains backend-neutral content/geometry used for cross-format
    rebuilds. ``native_payload`` is opaque to Common and may be used by the
    matching backend to preserve format-native fidelity (for example HWPX line
    layout caches and package resources).
    """

    source_format: str
    portable: dict[str, Any]
    native_payload: dict[str, Any] = field(default_factory=dict)


__all__ = ["DocumentSnapshot"]
