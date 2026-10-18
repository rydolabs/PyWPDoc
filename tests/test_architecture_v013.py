"""v0.13 architecture gates: independent backends, thin common facade, one-way deps."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pywpdoc._engine.common import Document as CommonDocument
from pywpdoc._engine.core.contracts import DocumentBackend

ROOT = Path(__file__).resolve().parents[1] / "src" / "pywpdoc" / "_engine"


def _backend_class(kind: str):
    if kind == "hwpx":
        from pywpdoc._engine.hwpx import Document
    else:
        from pywpdoc._engine.docx import Document
    return Document


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_common_returns_backend_owned_objects(kind: str):
    backend_cls = _backend_class(kind)
    direct = backend_cls.new()
    direct_p = direct.add_paragraph("direct")
    direct_t = direct.add_table(1, 1, style="Table Grid")

    doc = CommonDocument.new(kind)
    assert isinstance(doc.backend, DocumentBackend)
    p = doc.add_paragraph("backend-owned")
    t = doc.add_table(1, 1, style="Table Grid")

    # Common owns no paragraph/table object model. It returns the exact types
    # owned by the selected standalone backend, even when those types move into
    # smaller backend modules such as ``docx.paragraph``.
    assert type(p) is type(direct_p)
    assert type(t) is type(direct_t)
    assert type(t.cell(0, 0)) is type(direct_t.cell(0, 0))
    assert type(p).__module__.startswith(f"pywpdoc._engine.{kind}.")
    assert ".common" not in type(p).__module__


def test_common_is_thin_delegator_not_operation_owner():
    class FakeBackend:
        format = "fake"
        native = object()
        paragraphs = []
        tables = []
        sections = []
        def __init__(self): self.calls = []
        def add_paragraph(self, text="", style=None): self.calls.append(("add_paragraph", text, style)); return "P"
        def add_table(self, rows, cols, style=None): self.calls.append(("add_table", rows, cols, style)); return "T"
        def replace(self, search, replacement, *, everywhere=True, count=-1): self.calls.append(("replace", search, replacement, everywhere, count)); return 7
        def save(self, path): self.calls.append(("save", str(path)))
        def iter_inner_content(self): return iter(())

    backend = FakeBackend()
    doc = CommonDocument(backend)
    assert doc.add_paragraph("x") == "P"
    assert doc.add_table(2, 3) == "T"
    assert doc.replace("a", "b") == 7
    assert backend.calls[:3] == [
        ("add_paragraph", "x", None),
        ("add_table", 2, 3, None),
        ("replace", "a", "b", True, -1),
    ]
    # Operation implementations are backend methods reached through __getattr__.
    assert "add_table" not in CommonDocument.__dict__
    assert "replace" not in CommonDocument.__dict__


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_backend_is_standalone_without_common(kind: str, tmp_path: Path):
    if kind == "hwpx":
        from pywpdoc._engine.hwpx import Document
    else:
        from pywpdoc._engine.docx import Document

    doc = Document.new()
    p = doc.add_paragraph()
    p.add_run("202").bold = True
    p.add_run("6학년도").italic = True
    assert doc.replace("2026", "2027") == 1
    table = doc.add_table(1, 2, style="Table Grid")
    table.cell(0, 0).text = "outer"
    table.cell(0, 1).add_table(1, 1, style="Table Grid").cell(0, 0).text = "inner"
    path = tmp_path / f"standalone.{kind}"
    doc.save(path)
    reopened = Document.open(path)
    texts = [p.text for p in reopened.paragraphs]
    assert "2027학년도" in texts
    assert len(reopened.tables) == 1


def _imports(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            dots = "." * node.level
            result.append((node.lineno, dots + (node.module or "")))
    return result


def test_import_dependency_boundaries():
    common_files = list((ROOT / "common").glob("*.py"))
    docx_files = list((ROOT / "docx").glob("*.py"))
    hwpx_files = list((ROOT / "hwpx").glob("*.py"))
    core_files = list((ROOT / "core").glob("*.py"))

    violations = []
    for path in common_files:
        for line, name in _imports(path):
            if name == "docx" or name.startswith("docx."):
                violations.append((path.name, line, name, "common must not import python-docx"))
            if name in {"..document", "..model", "..authoring", "..package", "..styles"}:
                violations.append((path.name, line, name, "common must not import native HWPX implementation"))

    for path in docx_files:
        for line, name in _imports(path):
            if ".common" in name or ".hwpx" in name:
                violations.append((path.name, line, name, "DOCX backend must not depend on common/HWPX backend"))

    for path in hwpx_files:
        for line, name in _imports(path):
            if name == "docx" or name.startswith("docx.") or ".docx" in name or ".common" in name:
                violations.append((path.name, line, name, "HWPX backend must not depend on DOCX/common"))

    for path in core_files:
        for line, name in _imports(path):
            if any(token in name for token in (".common", ".docx", ".hwpx", "..document", "..model", "..authoring")):
                violations.append((path.name, line, name, "core must be implementation-independent"))

    assert violations == []


def _backend_geometry(kind: str, path: Path) -> tuple[int, int, int]:
    """Return persisted page width, top-level table width, nested table width in native units."""
    from zipfile import ZipFile
    from lxml import etree
    if kind == "hwpx":
        hp = "http://www.hancom.co.kr/hwpml/2011/paragraph"
        with ZipFile(path) as zf:
            root = etree.fromstring(zf.read("Contents/section0.xml"))
        ns = {"hp": hp}
        page = root.xpath(".//hp:pagePr", namespaces=ns)[0]
        outer = root.xpath("./hp:p/hp:run/hp:tbl", namespaces=ns)[0]
        outer_w = int(outer.xpath("./hp:sz", namespaces=ns)[0].get("width"))
        nested = outer.xpath(".//hp:tc/hp:subList/hp:p/hp:run/hp:tbl", namespaces=ns)[0]
        nested_w = int(nested.xpath("./hp:sz", namespaces=ns)[0].get("width"))
        return int(page.get("width")), outer_w, nested_w
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    with ZipFile(path) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
    ns = {"w": w}
    page = root.xpath(".//w:sectPr/w:pgSz", namespaces=ns)[-1]
    outer = root.xpath("./w:body/w:tbl", namespaces=ns)[0]
    outer_w = sum(int(c.get(f"{{{w}}}w")) for c in outer.xpath("./w:tblGrid/w:gridCol", namespaces=ns))
    nested = outer.xpath(".//w:tc/w:tbl", namespaces=ns)[0]
    nested_w = sum(int(c.get(f"{{{w}}}w")) for c in nested.xpath("./w:tblGrid/w:gridCol", namespaces=ns))
    return int(page.get(f"{{{w}}}w")), outer_w, nested_w


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_common_adds_no_geometry_behavior_over_standalone_backend(kind: str, tmp_path: Path):
    Document = _backend_class(kind)

    def author(doc):
        table = doc.add_table(1, 3, style="Table Grid")
        table.cell(0, 2).add_table(1, 2, style="Table Grid")
        return doc

    direct_path = tmp_path / f"direct.{kind}"
    common_path = tmp_path / f"common.{kind}"
    author(Document.new()).save(direct_path)
    author(CommonDocument.new(kind)).save(common_path)
    assert _backend_geometry(kind, direct_path) == _backend_geometry(kind, common_path)
