"""Original Common API contracts modeled on upstream document factory and properties."""
from __future__ import annotations
import zipfile
import pytest
from pywpdoc import Document
from pywpdoc._engine.core.errors import DocumentUnsupportedError, DocumentValueError


@pytest.mark.common_api
@pytest.mark.parametrize("value", ["", "Hello World", "한글 문서", "中文 العربية", "emoji 🧪", "escaped <&>"])
def test_document_paragraph_roundtrip(document, save_reopen, value):
    document.add_paragraph(value)
    opened, path = save_reopen(document)
    assert [p.text for p in opened.paragraphs] == [value]
    assert path.stat().st_size > 0


@pytest.mark.common_api
@pytest.mark.parametrize("texts", [("First", "Second"), ("A", "", "C"), ("가", "나", "다", "라")])
def test_document_paragraph_order_after_reopen(document, save_reopen, texts):
    for value in texts:
        document.add_paragraph(value)
    opened, _ = save_reopen(document)
    assert [p.text for p in opened.paragraphs] == list(texts)


@pytest.mark.common_api
@pytest.mark.parametrize("field,value", [("title", "Test title"), ("author", "QA Tester"), ("subject", "통합 문서")])
def test_core_metadata_is_persistent(document, save_reopen, field, value):
    setattr(document.core_properties, field, value)
    opened, _ = save_reopen(document)
    assert getattr(opened.core_properties, field) == value


@pytest.mark.common_api
def test_empty_document_save_reopen(document, save_reopen, common_format):
    opened, path = save_reopen(document)
    assert opened.format == common_format
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None


@pytest.mark.common_api
def test_format_and_native_backend_are_consistent(document, common_format):
    assert document.format == common_format
    assert document.unwrap() is document.native
    if common_format == "docx":
        assert document.docx is document.native
        with pytest.raises(DocumentUnsupportedError):
            _ = document.hwpx
    else:
        assert document.hwpx is document.native
        with pytest.raises(DocumentUnsupportedError):
            _ = document.docx


@pytest.mark.common_api
@pytest.mark.parametrize("bad_format", ["txt", "pdf", "", "doc", "hwp"])
def test_new_unknown_format_fails_closed(bad_format):
    with pytest.raises(DocumentValueError) as exc:
        Document.new(bad_format)
    assert exc.value.code == "common-format-invalid"


@pytest.mark.common_api
@pytest.mark.parametrize("suffix", [".txt", ".pdf", ".hwp"])
def test_open_unknown_format_fails_closed(tmp_path, suffix):
    p = tmp_path / ("unknown" + suffix)
    p.write_bytes(b"not a supported document")
    with pytest.raises(DocumentValueError) as exc:
        Document.open(p)
    assert exc.value.code == "common-format-unknown"


@pytest.mark.common_api
def test_compatibility_profile_is_specific_to_hwpx():
    assert Document.new("hwpx", compatibility="hancom2020").format == "hwpx"
    with pytest.raises(DocumentValueError) as exc:
        Document.new("docx", compatibility="hancom2020")
    assert exc.value.code == "common-compatibility-not-applicable"
