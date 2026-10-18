from __future__ import annotations

import pytest

from pywpdoc import Document, DocumentUnsupportedError, DocumentValueError
from pywpdoc.features.template.structure import (
    SectionKind,
    TableRowRepeatPlan,
    parse_section_blocks,
)


def test_structural_parser_pairs_nested_sections_without_document_dependency() -> None:
    text = "{{#customer}}A {{#items}}{{name}}{{/items}} B{{/customer}}"
    blocks = parse_section_blocks(text)
    assert [(block.key, block.kind) for block in blocks] == [
        ("customer", SectionKind.NORMAL),
        ("items", SectionKind.NORMAL),
    ]
    assert text[blocks[1].content_start:blocks[1].content_end] == "{{name}}"


def test_structural_parser_supports_inverted_section_model() -> None:
    [block] = parse_section_blocks("{{^items}}empty{{/items}}")
    assert block.key == "items"
    assert block.kind == SectionKind.INVERTED


def test_structural_parser_rejects_mismatched_sections() -> None:
    with pytest.raises(DocumentValueError) as excinfo:
        parse_section_blocks("{{#a}}x{{/b}}")
    assert excinfo.value.code == "template-section-mismatch"


def test_table_row_repeat_plan_contains_no_backend_object_contract() -> None:
    token = object()
    plan = TableRowRepeatPlan(key="items", row_token=token)
    assert plan.key == "items"
    assert plan.row_token is token
    assert plan.remove_template_row is True


def test_public_v1_renderer_still_fails_closed_for_sections() -> None:
    # v0.26 introduces only the pure structural parser/model.  It must not
    # silently alter the stable v0.25 rendering contract.
    doc = Document.new("hwpx")
    doc.add_paragraph("{{#items}}{{name}}{{/items}}")
    with pytest.raises(DocumentUnsupportedError) as excinfo:
        doc.render_template({"items": [{"name": "A"}]}, everywhere=False)
    assert excinfo.value.code == "template-control-not-supported-v1"
