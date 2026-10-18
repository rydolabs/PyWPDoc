"""v0.20 metadata/core-properties backend isolation regression."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from pywpdoc._engine.common import Document as CommonDocument


def _backend(kind: str):
    if kind == "hwpx":
        from pywpdoc._engine.hwpx import Document
    else:
        from pywpdoc._engine.docx import Document
    return Document


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_core_properties_are_backend_owned(kind: str):
    Document = _backend(kind)
    props = Document.new().core_properties
    assert type(props).__module__ == f"pywpdoc._engine.{kind}.metadata"
    assert type(props).__name__ == "CoreProperties"
    assert props.native is not None


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_common_delegates_backend_owned_core_properties(kind: str):
    direct = _backend(kind).new().core_properties
    common = CommonDocument.new(kind).core_properties
    assert type(common) is type(direct)
    assert type(common).__module__ == f"pywpdoc._engine.{kind}.metadata"
    assert "core_properties" not in CommonDocument.__dict__


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_core_properties_shared_fields_roundtrip(kind: str, tmp_path: Path):
    Document = _backend(kind)
    doc = Document.new()
    props = doc.core_properties
    props.title = "Metadata Contract"
    props.author = "Tester"
    props.subject = "Backend-owned metadata"
    props.comments = "roundtrip"
    props.keywords = "hwpx,docx"
    props.language = "ko-KR"
    props.last_modified_by = "pytest"

    out = tmp_path / f"metadata.{kind}"
    doc.save(out)
    rp = Document.open(out).core_properties
    assert rp.title == "Metadata Contract"
    assert rp.author == "Tester"
    assert rp.subject == "Backend-owned metadata"
    assert rp.comments == "roundtrip"
    assert rp.keywords == "hwpx,docx"
    assert rp.language == "ko-KR"
    assert rp.last_modified_by == "pytest"


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_core_properties_datetime_contract_is_utc_naive_seconds(kind: str, tmp_path: Path):
    Document = _backend(kind)
    doc = Document.new()
    props = doc.core_properties
    aware = datetime(2026, 10, 5, 17, 42, 33, 987654, tzinfo=timezone(timedelta(hours=9)))
    expected = datetime(2026, 10, 5, 8, 42, 33)
    props.created = aware
    props.modified = aware

    # Portable backend contract is UTC-naive with package-supported second precision.
    assert props.created == expected
    assert props.modified == expected

    out = tmp_path / f"metadata-date.{kind}"
    doc.save(out)
    rp = Document.open(out).core_properties
    assert rp.created == expected
    assert rp.modified == expected


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_core_properties_none_string_values_normalize_to_empty(kind: str, tmp_path: Path):
    Document = _backend(kind)
    doc = Document.new()
    props = doc.core_properties
    props.title = None
    props.author = None
    out = tmp_path / f"metadata-none.{kind}"
    doc.save(out)
    rp = Document.open(out).core_properties
    assert rp.title == ""
    assert rp.author == ""
