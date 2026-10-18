"""Public paragraph and Run contracts adapted by behavior, not source copy."""
from __future__ import annotations
import pytest


@pytest.mark.common_api
@pytest.mark.parametrize("parts", [("A", "B"), ("한", "글", "English"), ("first ", "second", " third"), ("", "data")])
def test_runs_concatenate_in_order(document, save_reopen, parts):
    p = document.add_paragraph()
    for part in parts:
        p.add_run(part)
    assert p.text == "".join(parts)
    reopened, _ = save_reopen(document)
    assert reopened.paragraphs[-1].text == "".join(parts)


@pytest.mark.common_api
@pytest.mark.parametrize("bold,italic", [(False, False), (True, False), (False, True), (True, True)])
def test_run_bold_italic_persist(document, save_reopen, bold, italic):
    p = document.add_paragraph()
    run = p.add_run("강조 텍스트")
    run.bold, run.italic = bold, italic
    opened, _ = save_reopen(document)
    visible = [r for r in opened.paragraphs[-1].runs if r.text]
    assert len(visible) == 1
    assert bool(visible[0].bold) is bold
    assert bool(visible[0].italic) is italic


@pytest.mark.common_api
@pytest.mark.parametrize("new_value", ["", "새 값", "longer replacement", "이모지 😀"])
def test_paragraph_text_setter_overwrites_content(document, save_reopen, new_value):
    p = document.add_paragraph()
    p.add_run("old ")
    p.add_run("value")
    p.text = new_value
    opened, _ = save_reopen(document)
    assert opened.paragraphs[-1].text == new_value


@pytest.mark.common_api
@pytest.mark.parametrize("new_value", ["바뀜", "A B C", "2026"])
def test_paragraph_clear_then_add_run(document, save_reopen, new_value):
    p = document.add_paragraph()
    p.add_run("will disappear")
    p.clear()
    p.add_run(new_value)
    opened, _ = save_reopen(document)
    assert opened.paragraphs[-1].text == new_value


@pytest.mark.common_api
@pytest.mark.parametrize("before", ["선행", "Inserted"])
def test_insert_paragraph_before_keeps_sequence(document, save_reopen, before):
    document.add_paragraph("after").insert_paragraph_before(before)
    opened, _ = save_reopen(document)
    assert [p.text for p in opened.paragraphs] == [before, "after"]


@pytest.mark.common_api
def test_independent_paragraph_run_mutation(document, save_reopen):
    p1 = document.add_paragraph("alpha")
    p2 = document.add_paragraph("beta")
    p1.runs[0].text = "ALPHA"
    assert p2.text == "beta"
    opened, _ = save_reopen(document)
    assert [x.text for x in opened.paragraphs] == ["ALPHA", "beta"]
