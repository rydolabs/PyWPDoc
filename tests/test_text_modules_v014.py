"""v0.14 paragraph/text module isolation and backend-level behavior gates."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pywpdoc._engine.core.errors import DocumentValueError

ROOT = Path(__file__).resolve().parents[1] / "src" / "pywpdoc" / "_engine"


def _backend_class(kind: str):
    if kind == "hwpx":
        from pywpdoc._engine.hwpx import Document
    else:
        from pywpdoc._engine.docx import Document
    return Document


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append("." * node.level + (node.module or ""))
    return names


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_paragraph_and_text_modules_have_narrow_dependencies(kind: str):
    paragraph = ROOT / kind / "paragraph.py"
    text = ROOT / kind / "text.py"
    assert paragraph.exists() and text.exists()

    opposite = f".{('docx' if kind == 'hwpx' else 'hwpx')}"
    paragraph_imports = _imports(paragraph)
    text_imports = _imports(text)
    # Paragraph may depend one-way on the small styles boundary because style
    # is part of its public object surface. Text mutation stays independent.
    assert not [name for name in paragraph_imports if any(token in name for token in (".common", opposite, ".table"))]
    assert not [name for name in text_imports if any(token in name for token in (".common", opposite, ".table", ".styles"))]

    # paragraph wrappers may depend on text/styles, never on the monolithic
    # backend module. Text remains a leaf operation module.
    assert ".backend" not in paragraph_imports
    assert ".backend" not in text_imports


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_paragraph_replace_count_is_backend_owned(kind: str, tmp_path: Path):
    Document = _backend_class(kind)
    doc = Document.new()
    p = doc.add_paragraph()
    first = p.add_run("TOKEN one ")
    first.bold = True
    second = p.add_run("TOKEN two")
    second.italic = True

    assert p.replace("TOKEN", "X", count=1) == 1
    assert p.text == "X one TOKEN two"
    assert first.bold is True
    assert second.italic is True

    out = tmp_path / f"count.{kind}"
    doc.save(out)
    reopened = Document.open(out)
    assert reopened.paragraphs[-1].text == "X one TOKEN two"


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_document_replace_scope_is_backend_owned(kind: str):
    Document = _backend_class(kind)
    doc = Document.new()
    doc.add_paragraph("TOKEN")
    table = doc.add_table(1, 1, style="Table Grid")
    table.cell(0, 0).text = "TOKEN"

    if kind == "hwpx":
        doc.sections[0].header.text = "TOKEN"
        header_text = lambda: doc.sections[0].header.text
    else:
        header = doc.sections[0].header
        header.paragraphs[0].text = "TOKEN"
        header_text = lambda: header.paragraphs[0].text

    assert doc.replace("TOKEN", "BODY", everywhere=False) == 1
    assert doc.paragraphs[-1].text == "BODY"
    assert table.cell(0, 0).text == "TOKEN"
    assert header_text() == "TOKEN"

    assert doc.replace("TOKEN", "EVERYWHERE", everywhere=True) == 2
    assert table.cell(0, 0).text == "EVERYWHERE"
    assert header_text() == "EVERYWHERE"


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_empty_search_error_contract_remains_backend_local(kind: str):
    Document = _backend_class(kind)
    doc = Document.new()
    with pytest.raises(DocumentValueError) as exc:
        doc.replace("", "x")
    assert exc.value.code == "text-search-empty"


def test_backend_modules_delegate_text_instead_of_owning_algorithm():
    for kind in ("hwpx", "docx"):
        source = (ROOT / kind / "backend.py").read_text(encoding="utf-8")
        assert "class Paragraph(" not in source
        assert "def _replace_paragraph(" not in source
        assert "from .paragraph import Paragraph, Run" in source
        assert "from .text import replace_document" in source

@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_new_run_does_not_inherit_previous_sibling_direct_formatting(kind: str, tmp_path: Path):
    Document = _backend_class(kind)
    doc = Document.new()
    p = doc.add_paragraph()
    first = p.add_run("first")
    first.bold = True
    second = p.add_run(" second")
    second.italic = True

    assert first.bold is True
    assert second.italic is True
    # Backends may represent inherited false as False or None, but the second
    # run must not visually inherit the first run's direct bold formatting.
    assert second.bold in (False, None)

    out = tmp_path / f"run-isolation.{kind}"
    doc.save(out)
    reopened = Document.open(out)
    visible = [r for r in reopened.paragraphs[-1].runs if r.text]
    assert visible[0].bold is True
    assert visible[1].italic is True
    assert visible[1].bold in (False, None)
