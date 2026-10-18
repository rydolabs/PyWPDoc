"""v0.16 style module isolation and standalone backend style contracts."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pywpdoc._engine.core import Pt, WD_STYLE_TYPE
from pywpdoc._engine.core.contracts import StylesBackend, StyleBackend

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
def test_styles_module_is_leaf_boundary(kind: str):
    styles = ROOT / kind / "styles.py"
    paragraph = ROOT / kind / "paragraph.py"
    assert styles.exists()
    imports = _imports(styles)
    opposite = "docx" if kind == "hwpx" else "hwpx"
    assert ".backend" not in imports
    assert not [name for name in imports if ".common" in name or f".{opposite}" in name]
    assert not [name for name in imports if any(token in name for token in (".paragraph", ".table", ".text"))]
    # Style is a public concern of Paragraph/Run, but dependency direction is
    # intentionally one-way so style maintenance cannot pull in text/table.
    assert ".styles" in _imports(paragraph)


def test_backend_modules_delegate_styles_instead_of_owning_implementation():
    for kind in ("hwpx", "docx"):
        source = (ROOT / kind / "backend.py").read_text(encoding="utf-8")
        assert "class Styles(" not in source
        assert "class Style(" not in source
        assert "from .styles import Styles" in source


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_style_public_types_are_backend_owned(kind: str):
    Document = _backend_class(kind)
    doc = Document.new()
    style = doc.styles.default(WD_STYLE_TYPE.PARAGRAPH)
    assert type(doc.styles).__module__ == f"pywpdoc._engine.{kind}.styles"
    assert style is not None
    assert type(style).__module__ == f"pywpdoc._engine.{kind}.styles"
    assert type(style.font).__module__ == f"pywpdoc._engine.{kind}.styles"
    assert type(style.paragraph_format).__module__ == f"pywpdoc._engine.{kind}.styles"


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_style_clone_is_independent_and_uses_shared_units(kind: str, tmp_path: Path):
    Document = _backend_class(kind)
    doc = Document.new()
    base_name = "Body" if kind == "hwpx" else "Normal"
    base = doc.styles.add_style("V016 Base", WD_STYLE_TYPE.PARAGRAPH, clone_from=base_name)
    base.font.bold = True
    base.font.size = Pt(14)
    base.font.color = "#336699"
    base.paragraph_format.space_before = Pt(6)

    clone = doc.styles.add_style("V016 Clone", WD_STYLE_TYPE.PARAGRAPH, clone_from=base)
    assert clone.font.bold is True
    assert clone.font.size is not None and abs(clone.font.size.pt - 14.0) < 0.03
    assert clone.font.color == "#336699"
    assert clone.paragraph_format.space_before is not None
    assert abs(clone.paragraph_format.space_before.pt - 6.0) < 0.03

    clone.font.italic = True
    clone.font.size = Pt(16)
    assert base.font.italic in (False, None)
    assert base.font.size is not None and abs(base.font.size.pt - 14.0) < 0.03

    out = tmp_path / f"styles-clone.{kind}"
    doc.save(out)
    reopened = Document.open(out)
    rb = reopened.styles["V016 Base"]
    rc = reopened.styles["V016 Clone"]
    assert rb.font.bold is True
    assert rb.font.italic in (False, None)
    assert rc.font.italic is True
    assert rc.font.size is not None and abs(rc.font.size.pt - 16.0) < 0.03
    assert rc.font.color == "#336699"


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_backend_style_objects_apply_to_paragraph_and_run(kind: str, tmp_path: Path):
    Document = _backend_class(kind)
    doc = Document.new()
    base_name = "Body" if kind == "hwpx" else "Normal"
    pstyle = doc.styles.add_style("V016 Paragraph", WD_STYLE_TYPE.PARAGRAPH, clone_from=base_name)
    pstyle.font.size = Pt(13)
    cstyle = doc.styles.add_style("V016 Character", WD_STYLE_TYPE.CHARACTER)
    cstyle.font.bold = True

    p = doc.add_paragraph("styled", style=pstyle)
    assert p.style is not None and p.style.name == "V016 Paragraph"
    r = p.add_run(" run", style=cstyle)
    assert r.style is not None and r.style.name == "V016 Character"
    assert r.style.font.bold is True

    out = tmp_path / f"style-apply.{kind}"
    doc.save(out)
    reopened = Document.open(out)
    rp = reopened.paragraphs[-1]
    assert rp.style is not None and rp.style.name == "V016 Paragraph"
    rr = [run for run in rp.runs if run.text][-1]
    assert rr.style is not None and rr.style.name == "V016 Character"


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_style_next_and_delete_are_backend_owned(kind: str, tmp_path: Path):
    Document = _backend_class(kind)
    doc = Document.new()
    base_name = "Body" if kind == "hwpx" else "Normal"
    a = doc.styles.add_style("V016 Question", WD_STYLE_TYPE.PARAGRAPH, clone_from=base_name)
    b = doc.styles.add_style("V016 Answer", WD_STYLE_TYPE.PARAGRAPH, clone_from=base_name)
    a.next_paragraph_style = b
    assert a.next_paragraph_style.name == "V016 Answer"

    disposable = doc.styles.add_style("V016 Delete", WD_STYLE_TYPE.PARAGRAPH, clone_from=base_name)
    disposable.delete()
    assert doc.styles.get("V016 Delete") is None

    out = tmp_path / f"style-life.{kind}"
    doc.save(out)
    reopened = Document.open(out)
    assert reopened.styles["V016 Question"].next_paragraph_style.name == "V016 Answer"
    assert reopened.styles.get("V016 Delete") is None


def test_common_returns_backend_owned_styles_without_style_logic():
    from pywpdoc._engine.common import Document as CommonDocument
    for kind in ("hwpx", "docx"):
        direct = _backend_class(kind).new()
        common = CommonDocument.new(kind)
        assert type(common.styles) is type(direct.styles)
        assert type(common.styles.default(WD_STYLE_TYPE.PARAGRAPH)) is type(direct.styles.default(WD_STYLE_TYPE.PARAGRAPH))
        assert ".common" not in type(common.styles).__module__


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_style_objects_satisfy_minimal_core_protocols(kind: str):
    Document = _backend_class(kind)
    doc = Document.new()
    assert isinstance(doc.styles, StylesBackend)
    style = doc.styles.default(WD_STYLE_TYPE.PARAGRAPH)
    assert style is not None and isinstance(style, StyleBackend)
