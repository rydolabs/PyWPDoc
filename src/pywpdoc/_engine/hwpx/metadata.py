"""HWPX-owned document metadata adapter.

The mature native HWPX engine owns ``Contents/content.hpf`` parsing and write
semantics.  This module only makes the verified core-properties surface belong
to the standalone HWPX backend instead of leaking the native facade type.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


class CoreProperties:
    """Backend-owned wrapper over the native HWPX core-properties facade."""

    def __init__(self, native: Any):
        self.native = native

    @property
    def title(self) -> str:
        return self.native.title

    @title.setter
    def title(self, value: str | None) -> None:
        self.native.title = value

    @property
    def author(self) -> str:
        return self.native.author

    @author.setter
    def author(self, value: str | None) -> None:
        self.native.author = value

    @property
    def subject(self) -> str:
        return self.native.subject

    @subject.setter
    def subject(self, value: str | None) -> None:
        self.native.subject = value

    @property
    def comments(self) -> str:
        return self.native.comments

    @comments.setter
    def comments(self, value: str | None) -> None:
        self.native.comments = value

    @property
    def keywords(self) -> str:
        return self.native.keywords

    @keywords.setter
    def keywords(self, value: str | None) -> None:
        self.native.keywords = value

    @property
    def language(self) -> str:
        return self.native.language

    @language.setter
    def language(self, value: str | None) -> None:
        self.native.language = value

    @property
    def last_modified_by(self) -> str:
        return self.native.last_modified_by

    @last_modified_by.setter
    def last_modified_by(self, value: str | None) -> None:
        self.native.last_modified_by = value

    @property
    def created(self) -> datetime | None:
        return self.native.created

    @created.setter
    def created(self, value: datetime | None) -> None:
        self.native.created = value

    @property
    def modified(self) -> datetime | None:
        return self.native.modified

    @modified.setter
    def modified(self, value: datetime | None) -> None:
        self.native.modified = value

    def __getattr__(self, name: str):
        return getattr(self.native, name)
