"""v0.43.0: conservative regex find/replace and existing API isolation."""
from __future__ import annotations

import hashlib
import re
import zipfile

import pytest

from pywpdoc import Document, DocumentUnsupportedError, DocumentValueError
from pywpdoc.core.text import TextMap
from pywpdoc.features.regex import RegexFindMatch


def _hashes(path):
    with zipfile.ZipFile(path) as zf:
        return {n: hashlib.sha256(zf.read(n)).hexdigest() for n in zf.namelist()}


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_regex_finds_dates_with_groups_offsets_and_replaces(fmt):
    d = Document.new(fmt)
    p = d.add_paragraph("회의: 2026-10-13, 재검토 2026-11-02")
    pattern = r"(?P<year>\d{4})-(?P<month>\d{2})-(\d{2})"
    matches = d.find_regex(pattern, everywhere=False)
    assert len(matches) == 2
    assert all(isinstance(m, RegexFindMatch) for m in matches)
    assert [m.text for m in matches] == ["2026-10-13", "2026-11-02"]
    assert matches[0].start == 4
    assert matches[0].groups == ("2026", "10", "13")
    assert matches[0].groupdict == {"year": "2026", "month": "10"}
    assert p.text == "회의: 2026-10-13, 재검토 2026-11-02"
    assert d.replace_regex(pattern, r"\g<year>.\g<month>.\3", everywhere=False) == 2
    assert p.text == "회의: 2026.10.13, 재검토 2026.11.02"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_regex_cross_run_preserves_format_and_suffix(fmt):
    d = Document.new(fmt)
    p = d.add_paragraph("")
    p.clear()
    a = p.add_run("앞 영문  AB")
    a.bold = True
    b = p.add_run("12 끝")
    b.italic = True
    assert [(m.start, m.end) for m in d.find_regex(r"AB\d{2}", everywhere=False)] == [(6, 10)]
    assert d.replace_regex(r"(AB)(\d{2})", r"\2-\1", everywhere=False) == 1
    assert p.text == "앞 영문  12-AB 끝"
    assert a.bold is True
    assert b.italic is True


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_regex_global_count_and_reverse_replace(fmt):
    d = Document.new(fmt)
    first = d.add_paragraph("aa11 bb22 cc33")
    second = d.add_paragraph("dd44")
    assert len(d.find_regex(r"[a-z]{2}\d{2}", everywhere=False, count=2)) == 2
    assert d.replace_regex(r"[a-z]{2}(\d{2})", r"<\1>", everywhere=False, count=2) == 2
    assert first.text == "<11> <22> cc33"
    assert second.text == "dd44"
    assert d.replace_regex(r"[a-z]{2}\d{2}", "X", everywhere=False) == 2
    assert first.text == "<11> <22> X"
    assert second.text == "X"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_regex_case_insensitive_and_unicode(fmt):
    d = Document.new(fmt)
    p = d.add_paragraph("고객 ALICE, 고객 alice, 고객 Bob")
    assert len(d.find_regex("alice", flags=re.IGNORECASE, everywhere=False)) == 2
    assert d.replace_regex(r"고객\s+(alice)", r"담당자 \1", flags=re.IGNORECASE, everywhere=False) == 2
    assert p.text == "담당자 ALICE, 담당자 alice, 고객 Bob"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_regex_body_only_and_table_header_footer(fmt):
    d = Document.new(fmt)
    d.add_paragraph("본문 ITEM-01")
    d.add_table(1, 1).cell(0, 0).text = "표 ITEM-02"
    d.sections[0].header.text = "머리말 ITEM-03"
    assert len(d.find_regex(r"ITEM-\d+", everywhere=False)) == 1
    assert len(d.find_regex(r"ITEM-\d+")) == 3
    assert d.replace_regex(r"ITEM-(\d+)", r"NO:\1", everywhere=False) == 1
    assert d.find("ITEM", everywhere=False) == []
    assert len(d.find_regex(r"ITEM-\d+")) == 2


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_zero_count_none_and_negative_limit(fmt):
    d = Document.new(fmt)
    p = d.add_paragraph("A1 B2 C3")
    assert d.find_regex(r"[A-Z]\d", everywhere=False, count=0) == []
    assert d.replace_regex(r"[A-Z]\d", "X", count=0, everywhere=False) == 0
    assert p.text == "A1 B2 C3"
    assert len(d.find_regex(r"[A-Z]\d", everywhere=False, count=None)) == 3
    assert d.replace_regex(r"[A-Z]\d", "Y", count=-10, everywhere=False) == 3
    assert p.text == "Y Y Y"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_unchanged_if_regex_no_match(fmt):
    d = Document.new(fmt)
    p = d.add_paragraph("원본")
    assert d.find_regex(r"\d+", everywhere=False) == []
    assert d.replace_regex(r"\d+", "R", everywhere=False) == 0
    assert p.text == "원본"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_named_optional_capture_and_empty_replacement(fmt):
    d = Document.new(fmt)
    p = d.add_paragraph("A-12, B, C-34")
    # Optional unmatched captures become empty in Python re Match.expand.
    assert d.replace_regex(r"(?P<letter>[ABC])(?:-(\d+))?", r"\g<letter>\2", everywhere=False) == 3
    assert p.text == "A12, B, C34"
    assert d.replace_regex(r"\d+", "", everywhere=False) == 2
    assert p.text == "A, B, C"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_existing_literal_find_preview_replace_preserved(fmt):
    d = Document.new(fmt)
    p = d.add_paragraph("A.1 A.2")
    assert len(d.find("A.", everywhere=False)) == 2
    assert d.preview_replace("A.", "Z", everywhere=False).count == 2
    assert d.replace_text("A.", "Z", everywhere=False) == 2
    assert p.text == "Z1 Z2"
    assert d.replace_regex(r"Z(\d)", r"Y\1", everywhere=False) == 2
    assert p.text == "Y1 Y2"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_save_reopen_roundtrip_and_package_preservation_for_find(fmt, tmp_path):
    d = Document.new(fmt)
    p = d.add_paragraph("제안서 2026-10-13")
    p.add_run(" / 내부검토")
    source = tmp_path / ("source." + fmt)
    after_find = tmp_path / ("after_find." + fmt)
    d.save(source)
    original = _hashes(source)
    assert len(d.find_regex(r"\d{4}-\d{2}-\d{2}")) == 1
    d.save(after_find)
    assert _hashes(after_find) == original
    reopened = Document.open(source)
    assert reopened.replace_regex(r"(\d{4})-(\d\d)-(\d\d)", r"\1/\2/\3") == 1
    final = tmp_path / ("final." + fmt)
    reopened.save(final)
    again = Document.open(final)
    assert len(again.find_regex(r"2026/10/13")) == 1
    assert len(again.find_regex(r"내부검토")) == 1


@pytest.mark.parametrize("pattern,expected_code", [
    ("", "regex-pattern-empty"),
    ("(", "regex-pattern-invalid"),
    ("[z-", "regex-pattern-invalid"),
    (r"\b", "regex-zero-width"),
    (r"a*", "regex-zero-width"),
    (r"^", "regex-zero-width"),
])
def test_invalid_or_empty_regex_fails_closed(pattern, expected_code):
    d = Document.new("docx")
    p = d.add_paragraph("aaa")
    error_type = DocumentUnsupportedError if expected_code == "regex-zero-width" else DocumentValueError
    with pytest.raises(error_type) as err:
        d.replace_regex(pattern, "X", everywhere=False)
    assert err.value.code == expected_code
    assert p.text == "aaa"


def test_later_zero_width_found_preflight_before_any_mutation():
    d = Document.new("docx")
    first = d.add_paragraph("foo")
    second = d.add_paragraph("abc")
    # Lookbehind does not match the empty input but is zero-width in 'abc'.
    with pytest.raises(DocumentUnsupportedError) as err:
        d.replace_regex(r"foo|(?<=a)", "X", everywhere=False)
    assert err.value.code == "regex-zero-width"
    assert first.text == "foo"
    assert second.text == "abc"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_bad_replacement_group_does_not_partially_write(fmt):
    d = Document.new(fmt)
    p = d.add_paragraph("abc 123")
    with pytest.raises(DocumentValueError) as exc:
        d.replace_regex(r"\w+", r"\g<missing>", everywhere=False)
    assert exc.value.code == "regex-replacement-invalid"
    assert p.text == "abc 123"


def test_bad_replacement_after_first_match_does_not_write():
    d = Document.new("docx")
    p = d.add_paragraph("foo:abc bar:9")
    # The referenced optional group exists for first hit, not second: Python
    # substitutes empty for unmatched captures, so both are valid.
    assert d.replace_regex(r"(foo|bar):([a-z]+|\d+)", r"\1=\2", everywhere=False) == 2
    assert p.text == "foo=abc bar=9"


def test_negative_cases_for_count_replacement_and_flags():
    d = Document.new("docx")
    p = d.add_paragraph("abc 123")
    for params, code in [
        ({"count": "bad"}, "regex-count-invalid"),
        ({"flags": re.LOCALE}, "regex-pattern-invalid"),
    ]:
        with pytest.raises(DocumentValueError) as exc:
            d.replace_regex(r"[a-z]+", "X", everywhere=False, **params)
        assert exc.value.code == code
    with pytest.raises(DocumentValueError) as exc:
        d.replace_regex(r"[a-z]+", None, everywhere=False)
    assert exc.value.code == "regex-replacement-invalid"
    assert p.text == "abc 123"


def test_find_captures_are_snapshots_even_after_mutation():
    d = Document.new("docx")
    p = d.add_paragraph("A12 B34")
    matches = d.find_regex(r"(?P<prefix>[A-Z])(\d+)")
    assert matches[0].groupdict == {"prefix": "A"}
    d.replace_regex(r"[A-Z]\d+", "X")
    assert p.text == "X X"
    assert matches[0].text == "A12"
    assert matches[1].groups == ("B", "34")


def test_docx_field_and_revision_boundaries_are_skipped_not_consumed():
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    d = Document.new("docx")
    unsafe = d.add_paragraph("")
    unsafe.clear()
    unsafe.add_run("AB")
    native_r = unsafe.add_run("").native._r
    marker = OxmlElement("w:fldChar")
    marker.set(qn("w:fldCharType"), "begin")
    native_r.append(marker)
    end_marker = OxmlElement("w:fldChar")
    end_marker.set(qn("w:fldCharType"), "end")
    native_r.append(end_marker)
    unsafe.add_run("12")
    safe = d.add_paragraph("AB12")
    assert TextMap.from_paragraph(unsafe).unsafe_boundaries
    assert len(d.find_regex(r"AB\d+", everywhere=False, count=1)) == 1
    assert d.replace_regex(r"(AB)(\d+)", r"\2\1", everywhere=False, count=1) == 1
    assert TextMap.from_paragraph(unsafe).text == "AB12"
    assert safe.text == "12AB"


def test_docx_single_run_multinode_replacement():
    from docx.oxml import OxmlElement
    d = Document.new("docx")
    p = d.add_paragraph("")
    p.clear()
    run = p.add_run("")
    for text in ("A", "B", "12"):
        t = OxmlElement("w:t")
        t.text = text
        run.native._r.append(t)
    assert len(TextMap.from_paragraph(p).segments) == 3
    assert d.replace_regex(r"AB(\d+)", r"NO\1", everywhere=False) == 1
    assert p.text == "NO12"
    assert len(run.native._r.findall("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")) == 3


def test_invalid_pattern_in_find_does_not_change_document():
    d = Document.new("docx")
    p = d.add_paragraph("abc")
    with pytest.raises(DocumentValueError):
        d.find_regex("[", everywhere=False)
    assert p.text == "abc"
