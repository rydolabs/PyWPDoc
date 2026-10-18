"""Advanced, differentiating Common API: regex and template safety."""
from __future__ import annotations
import re
import pytest
from pywpdoc._engine.core.errors import DocumentUnsupportedError, DocumentValueError


@pytest.mark.common_api
@pytest.mark.parametrize("text,pat,repl,expected", [
    ("2026-10-15", r"(\d{4})-(\d{2})-(\d{2})", r"\3/\2/\1", "15/10/2026"),
    ("CODE-007", r"CODE-(\d+)", r"ID-\1", "ID-007"),
    ("abc DEF", r"[A-Za-z]+", "X", "X X"),
    ("alpha", r"z+", "X", "alpha"),
])
def test_regex_replace_has_expected_result(document, save_reopen, text, pat, repl, expected):
    document.add_paragraph(text)
    document.replace_regex(pat, repl)
    opened, _ = save_reopen(document)
    assert opened.paragraphs[0].text == expected


@pytest.mark.common_api
@pytest.mark.parametrize("pattern,err", [("(", "regex-pattern-invalid"), (r"(?=alpha)", "regex-zero-width")])
def test_regex_bad_pattern_fails_without_mutation(document, pattern, err):
    document.add_paragraph("alpha")
    with pytest.raises((DocumentUnsupportedError, DocumentValueError)) as exc:
        document.replace_regex(pattern, "X")
    assert exc.value.code == err
    assert document.paragraphs[0].text == "alpha"


@pytest.mark.common_api
def test_regex_invalid_capture_preflight_is_atomic(document):
    document.add_paragraph("a1")
    document.add_paragraph("b2")
    with pytest.raises(DocumentValueError) as exc:
        document.replace_regex(r"([a-z])(\d)", r"\g<unknown>")
    assert exc.value.code == "regex-replacement-invalid"
    assert [p.text for p in document.paragraphs] == ["a1", "b2"]


@pytest.mark.common_api
def test_regex_find_is_readonly(document, save_reopen):
    document.add_paragraph("AB-12 XY-34")
    assert len(document.find_regex(r"[A-Z]{2}-\d+")) == 2
    assert document.paragraphs[0].text == "AB-12 XY-34"
    opened, _ = save_reopen(document)
    assert opened.paragraphs[0].text == "AB-12 XY-34"


@pytest.mark.common_api
@pytest.mark.parametrize("name", ["Alice", "홍길동", "😀", "<>&\""])
def test_template_scalar_roundtrip(document, save_reopen, name):
    document.add_paragraph("Hello {{name}}!")
    assert document.render_template({"name": name}) == 1
    opened, _ = save_reopen(document)
    assert opened.paragraphs[0].text == f"Hello {name}!"


@pytest.mark.common_api
@pytest.mark.parametrize("policy,expected", [("keep", "Missing {{not_found}}"), ("empty", "Missing ")])
def test_template_missing_policy(document, save_reopen, policy, expected):
    document.add_paragraph("Missing {{not_found}}")
    document.render_template({}, missing=policy)
    opened, _ = save_reopen(document)
    assert opened.paragraphs[0].text == expected


@pytest.mark.common_api
def test_template_missing_error_is_atomic_across_paragraphs_and_table(document):
    document.add_paragraph("Found {{name}}")
    document.add_table(1, 1).cell(0, 0).text = "Missing {{absent}}"
    with pytest.raises(DocumentValueError) as exc:
        document.render_template({"name": "OK"}, missing="error", everywhere=True)
    assert exc.value.code == "template-value-missing"
    assert document.paragraphs[0].text == "Found {{name}}"
    assert document.tables[0].cell(0, 0).text == "Missing {{absent}}"


@pytest.mark.common_api
def test_template_check_is_read_only(document):
    document.add_paragraph("Welcome {{visitor}}")
    document.check_template({"visitor": "name"})
    assert document.paragraphs[0].text == "Welcome {{visitor}}"


@pytest.mark.common_api
def test_template_plain_data_never_recursively_reinterpreted(document):
    document.add_paragraph("Value={{x}}")
    document.render_template({"x": "{{secret}}"})
    assert document.paragraphs[0].text == "Value={{secret}}"
