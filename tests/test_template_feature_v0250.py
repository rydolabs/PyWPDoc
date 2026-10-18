from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from pywpdoc import Document, DocumentUnsupportedError, DocumentValueError
from pywpdoc.features.template import (
    iter_variable_tags,
    render_template,
    resolve_value,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "tests/baseline/v0215_manifest.json").read_text(encoding="utf-8"))


def _zip_hashes(path: Path, selected: set[str] | None = None) -> dict[str, str]:
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        if selected is not None:
            names &= selected
        return {name: hashlib.sha256(zf.read(name)).hexdigest() for name in sorted(names)}


def test_template_parser_is_pure_and_tracks_logical_offsets() -> None:
    text = "Hello {{ customer.name }} / {{date}}"
    tags = list(iter_variable_tags(text))
    assert [(t.key, t.raw, text[t.start:t.end]) for t in tags] == [
        ("customer.name", "{{ customer.name }}", "{{ customer.name }}"),
        ("date", "{{date}}", "{{date}}"),
    ]


def test_template_context_resolves_mapping_dotted_name_and_object_attribute() -> None:
    @dataclass
    class Customer:
        name: str

    assert resolve_value({"customer": {"name": "Acme"}}, "customer.name").value == "Acme"
    assert resolve_value({"customer": Customer("Beta")}, "customer.name").value == "Beta"
    assert resolve_value({"customer": {}}, "customer.name").found is False


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_render_template_uses_same_api_for_both_backends(kind: str) -> None:
    doc = Document.new(kind)
    doc.add_paragraph("고객: {{customer.name}} / 날짜: {{date}}")
    table = doc.add_table(1, 1)
    table.cell(0, 0).text = "금액 {{amount}}"
    doc.sections[0].header.text = "{{customer.name}} 안내"

    changed = doc.render_template({
        "customer": {"name": "Acme"},
        "date": "2026-10-06",
        "amount": 12000,
    })

    assert changed == 4
    assert doc.paragraphs[-1].text == "고객: Acme / 날짜: 2026-10-06"
    assert table.cell(0, 0).text == "금액 12000"
    assert "Acme 안내" in doc.sections[0].header.text


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_render_template_handles_tag_split_across_runs_and_preserves_surviving_format(kind: str) -> None:
    doc = Document.new(kind)
    paragraph = doc.add_paragraph("")
    paragraph.clear()
    first = paragraph.add_run("Name: {{cus")
    first.bold = True
    second = paragraph.add_run("tomer.name}}!")
    second.italic = True

    assert doc.render_template({"customer": {"name": "홍길동"}}, everywhere=False) == 1
    assert paragraph.text == "Name: 홍길동!"
    assert first.text == "Name: 홍길동"
    assert second.text == "!"
    assert first.bold is True
    assert second.italic is True


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_template_missing_policies_are_explicit(kind: str) -> None:
    keep = Document.new(kind)
    keep.add_paragraph("A {{missing}} B")
    assert keep.render_template({}, everywhere=False) == 0
    assert keep.paragraphs[-1].text == "A {{missing}} B"

    empty = Document.new(kind)
    empty.add_paragraph("A {{missing}} B")
    assert empty.render_template({}, everywhere=False, missing="empty") == 1
    assert empty.paragraphs[-1].text == "A  B"

    error = Document.new(kind)
    error.add_paragraph("A {{missing}} B")
    with pytest.raises(DocumentValueError) as excinfo:
        error.render_template({}, everywhere=False, missing="error")
    assert excinfo.value.code == "template-value-missing"


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_template_rejects_invalid_missing_policy(kind: str) -> None:
    doc = Document.new(kind)
    doc.add_paragraph("{{name}}")
    with pytest.raises(DocumentValueError) as excinfo:
        doc.render_template({"name": "A"}, missing="invalid")
    assert excinfo.value.code == "template-missing-policy-invalid"


def test_template_v1_rejects_control_tags_instead_of_silently_misrendering() -> None:
    doc = Document.new("hwpx")
    doc.add_paragraph("{{#items}}X{{/items}}")
    with pytest.raises(DocumentUnsupportedError) as excinfo:
        doc.render_template({"items": [1]}, everywhere=False)
    assert excinfo.value.code == "template-control-not-supported-v1"


def test_template_function_can_target_backend_directly() -> None:
    doc = Document.new("hwpx")
    paragraph = doc.add_paragraph("Hello {{name}}")
    assert render_template(doc.backend, {"name": "World"}, everywhere=False) == 1
    assert paragraph.text == "Hello World"


def test_template_does_not_depend_on_sibling_features() -> None:
    package = ROOT / "src/pywpdoc/features/template"
    source = "\n".join(path.read_text(encoding="utf-8") for path in package.rglob("*.py"))
    assert "features.find" not in source
    assert "features.replace" not in source


def test_template_noop_preserves_v0215_hwpx_golden(tmp_path: Path) -> None:
    source = ROOT / MANIFEST["source_fixture"]
    doc = Document.open(source)
    assert doc.render_template({"unused": "X"}) == 0
    out = tmp_path / "noop-template.hwpx"
    doc.save(out)
    assert _zip_hashes(out) == MANIFEST["hwpx_package_parts"]


def test_template_noop_preserves_docx_package_parts(tmp_path: Path) -> None:
    source = ROOT / MANIFEST["source_fixture"]
    selected = set(MANIFEST["docx_selected_parts"])

    baseline = Document.rebuild(source, format="docx", preserve_layout=True)
    before = tmp_path / "before.docx"
    baseline.save(before)

    changed = Document.rebuild(source, format="docx", preserve_layout=True)
    assert changed.render_template({"unused": "X"}) == 0
    after = tmp_path / "after.docx"
    changed.save(after)

    assert _zip_hashes(after, selected) == _zip_hashes(before, selected)
    assert _zip_hashes(after, selected) == MANIFEST["docx_selected_parts"]
