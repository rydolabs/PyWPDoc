"""Document-level search/replace: positive, negative and read-only behavior."""
from __future__ import annotations
import pytest
from pywpdoc._engine.core.errors import DocumentValueError


@pytest.mark.common_api
@pytest.mark.parametrize("query,expected", [("TOKEN", 3), ("token", 0), ("absent", 0), ("before", 1)])
def test_find_is_read_only(document, query, expected):
    document.add_paragraph("TOKEN before TOKEN")
    document.add_paragraph("TOKEN after")
    before = [p.text for p in document.paragraphs]
    assert len(document.find(query, case_sensitive=True)) == expected
    assert [p.text for p in document.paragraphs] == before


@pytest.mark.common_api
@pytest.mark.parametrize("case_sensitive,expected", [(True, 1), (False, 3)])
def test_find_case_sensitive_switch(document, case_sensitive, expected):
    document.add_paragraph("Alpha alpha ALPHA")
    assert len(document.find("alpha", case_sensitive=case_sensitive)) == expected


@pytest.mark.common_api
@pytest.mark.parametrize("limit,expected", [(0,0), (1,1), (2,2), (3,3), (-1,3)])
def test_replace_count_global_limit(document, save_reopen, limit, expected):
    document.add_paragraph("old old")
    document.add_paragraph("old")
    assert document.replace_text("old", "new", count=limit) == expected
    opened, _ = save_reopen(document)
    assert " ".join(x.text for x in opened.paragraphs).count("new") == expected


@pytest.mark.common_api
@pytest.mark.parametrize("needle,replacement,expected", [("alpha", "X", "X"), ("aLpHa", "Y", "Y"), ("none", "Z", "Alpha")])
def test_replace_case_insensitive_and_noop(document, needle, replacement, expected):
    document.add_paragraph("Alpha")
    document.replace_text(needle, replacement, case_sensitive=False)
    assert document.paragraphs[0].text == expected


@pytest.mark.common_api
def test_preview_no_mutation_before_and_after_save(document, save_reopen):
    document.add_paragraph("old old")
    before = [p.text for p in document.paragraphs]
    document.preview_replace("old", "future")
    assert [p.text for p in document.paragraphs] == before
    reopened, _ = save_reopen(document)
    assert [p.text for p in reopened.paragraphs] == before


@pytest.mark.common_api
def test_body_only_does_not_replace_table_cells(document, save_reopen):
    document.add_paragraph("old body")
    table = document.add_table(1, 1)
    table.cell(0, 0).text = "old table"
    assert document.replace_text("old", "new", everywhere=False) == 1
    reopened, _ = save_reopen(document)
    assert reopened.paragraphs[0].text == "new body"
    assert reopened.tables[0].cell(0, 0).text == "old table"


@pytest.mark.common_api
def test_everywhere_includes_table_cells(document, save_reopen):
    document.add_paragraph("old body")
    document.add_table(1, 1).cell(0, 0).text = "old table"
    assert document.replace_text("old", "new", everywhere=True) == 2
    reopened, _ = save_reopen(document)
    assert reopened.tables[0].cell(0, 0).text == "new table"


@pytest.mark.common_api
def test_empty_search_rejected_without_changes(document):
    document.add_paragraph("preserve")
    with pytest.raises(DocumentValueError) as exc:
        document.replace_text("", "no")
    assert exc.value.code == "replace-query-empty"
    assert document.paragraphs[0].text == "preserve"
