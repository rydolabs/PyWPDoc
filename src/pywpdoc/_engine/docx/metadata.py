"""DOCX-owned document metadata adapter.

All python-docx CoreProperties adaptation lives here.  The shared portable
surface intentionally follows the existing HWPX contract, including UTC-naive
datetime values, while the original python-docx object remains available as
``.native`` for format-specific behavior.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _portable_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.replace(microsecond=0)


class CoreProperties:
    """Backend-owned wrapper over ``python-docx`` core properties."""

    def __init__(self, native: Any):
        self.native = native

    @property
    def title(self) -> str:
        return self.native.title

    @title.setter
    def title(self, value: str | None) -> None:
        self.native.title = "" if value is None else str(value)

    @property
    def author(self) -> str:
        return self.native.author

    @author.setter
    def author(self, value: str | None) -> None:
        self.native.author = "" if value is None else str(value)

    @property
    def subject(self) -> str:
        return self.native.subject

    @subject.setter
    def subject(self, value: str | None) -> None:
        self.native.subject = "" if value is None else str(value)

    @property
    def comments(self) -> str:
        return self.native.comments

    @comments.setter
    def comments(self, value: str | None) -> None:
        self.native.comments = "" if value is None else str(value)

    @property
    def keywords(self) -> str:
        return self.native.keywords

    @keywords.setter
    def keywords(self, value: str | None) -> None:
        self.native.keywords = "" if value is None else str(value)

    @property
    def language(self) -> str:
        return self.native.language

    @language.setter
    def language(self, value: str | None) -> None:
        self.native.language = "" if value is None else str(value)

    @property
    def last_modified_by(self) -> str:
        return self.native.last_modified_by

    @last_modified_by.setter
    def last_modified_by(self, value: str | None) -> None:
        self.native.last_modified_by = "" if value is None else str(value)

    @property
    def created(self) -> datetime | None:
        return _portable_datetime(self.native.created)

    @created.setter
    def created(self, value: datetime | None) -> None:
        self.native.created = _portable_datetime(value)

    @property
    def modified(self) -> datetime | None:
        return _portable_datetime(self.native.modified)

    @modified.setter
    def modified(self, value: datetime | None) -> None:
        self.native.modified = _portable_datetime(value)

    def __getattr__(self, name: str):
        return getattr(self.native, name)
