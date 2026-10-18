"""Invalid inputs, rejections and non-destructive failures."""
from __future__ import annotations
import re
import zipfile
import pytest
from pywpdoc import Document
from pywpdoc._engine.core.errors import DocumentValueError, DocumentUnsupportedError


@pytest.mark.common_api
@pytest.mark.negative
@pytest.mark.parametrize("bad", [b"", b"garbage", b"PK\x03\x04garbage", b"<xml/>"])
@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_corrupt_archive_never_loads_as_valid_document(fmt, bad, tmp_path):
    p = tmp_path / ("broken." + fmt)
    p.write_bytes(bad)
    with pytest.raises(Exception):
        Document.open(p)


@pytest.mark.common_api
@pytest.mark.negative
@pytest.mark.parametrize("replacement", [r"\g<missing>", r"\7"])
def test_invalid_regex_capture_must_not_partially_mutate(document, replacement):
    document.add_paragraph("a1")
    document.add_paragraph("b2")
    with pytest.raises(DocumentValueError) as exc:
        document.replace_regex(r"([a-z])(\d)", replacement)
    assert exc.value.code == "regex-replacement-invalid"
    assert [p.text for p in document.paragraphs] == ["a1", "b2"]


@pytest.mark.common_api
@pytest.mark.negative
@pytest.mark.parametrize("pattern", ["(", "[a-", "(?P<bad"])
def test_invalid_regex_syntax_preserves_original(document, pattern):
    document.add_paragraph("123")
    with pytest.raises(DocumentValueError) as exc:
        document.replace_regex(pattern, "result")
    assert exc.value.code == "regex-pattern-invalid"
    assert document.paragraphs[0].text == "123"


@pytest.mark.common_api
@pytest.mark.negative
@pytest.mark.parametrize("missing", ["error", "keep", "empty"])
def test_template_policy_has_explicit_defined_result(document, missing):
    document.add_paragraph("Hi {{name}}")
    if missing == "error":
        with pytest.raises(DocumentValueError):
            document.render_template({}, missing=missing)
        assert document.paragraphs[0].text == "Hi {{name}}"
    else:
        document.render_template({}, missing=missing)
        assert document.paragraphs[0].text == ("Hi {{name}}" if missing == "keep" else "Hi ")
