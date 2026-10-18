from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "src" / "pywpdoc" / "features"


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            prefix = "." * node.level
            found.append(prefix + module)
    return found


def test_features_do_not_depend_on_concrete_backends() -> None:
    forbidden_prefixes = (
        "pywpdoc.hwpx", "pywpdoc.docx",
        "pywpdoc._engine.hwpx", "pywpdoc._engine.docx",
        "docx", "lxml",
    )
    for path in FEATURES.rglob("*.py"):
        for imported in _imports(path):
            assert not imported.startswith(forbidden_prefixes), (path, imported)


def test_new_public_facade_does_not_own_format_logic() -> None:
    source = (ROOT / "src" / "pywpdoc" / "document.py").read_text(encoding="utf-8")
    assert "pywpdoc._engine.hwpx" not in source
    assert "pywpdoc._engine.docx" not in source
    assert "docx.oxml" not in source
    assert "lxml" not in source


def test_core_text_primitives_do_not_depend_on_concrete_backends() -> None:
    core_text = ROOT / "src" / "pywpdoc" / "core" / "text"
    forbidden_prefixes = (
        "pywpdoc.hwpx", "pywpdoc.docx",
        "pywpdoc._engine.hwpx", "pywpdoc._engine.docx",
        "docx", "lxml",
    )
    for path in core_text.rglob("*.py"):
        for imported in _imports(path):
            assert not imported.startswith(forbidden_prefixes), (path, imported)


def test_find_feature_is_composed_from_core_text_primitives() -> None:
    source = (ROOT / "src" / "pywpdoc" / "features" / "find" / "api.py").read_text(encoding="utf-8")
    assert "pywpdoc.core.text" in source
    assert "pywpdoc.hwpx" not in source
    assert "pywpdoc.docx" not in source
    assert "pywpdoc._engine.hwpx" not in source
    assert "pywpdoc._engine.docx" not in source


def test_feature_packages_do_not_import_sibling_features() -> None:
    feature_dirs = [p for p in FEATURES.iterdir() if p.is_dir() and not p.name.startswith("__")]
    names = {p.name for p in feature_dirs}
    for feature_dir in feature_dirs:
        siblings = names - {feature_dir.name}
        for path in feature_dir.rglob("*.py"):
            imports = _imports(path)
            for sibling in siblings:
                forbidden = (
                    f"pywpdoc.features.{sibling}",
                    f"..{sibling}",
                    f".{sibling}",
                )
                assert not any(item.startswith(forbidden) for item in imports), (path, imports)


def test_replace_feature_is_composed_from_core_text_primitives() -> None:
    source = (ROOT / "src" / "pywpdoc" / "features" / "replace" / "api.py").read_text(encoding="utf-8")
    assert "pywpdoc.core.text" in source
    assert "pywpdoc.features.find" not in source
    assert "pywpdoc.hwpx" not in source
    assert "pywpdoc.docx" not in source
    assert "pywpdoc._engine.hwpx" not in source
    assert "pywpdoc._engine.docx" not in source


def test_template_feature_is_composed_from_core_text_primitives() -> None:
    package = ROOT / "src" / "pywpdoc" / "features" / "template"
    source = "\n".join(path.read_text(encoding="utf-8") for path in package.rglob("*.py"))
    assert "pywpdoc.core.text" in source
    assert "pywpdoc.features.find" not in source
    assert "pywpdoc.features.replace" not in source
    assert "pywpdoc.hwpx" not in source
    assert "pywpdoc.docx" not in source
    assert "pywpdoc._engine.hwpx" not in source
    assert "pywpdoc._engine.docx" not in source


def test_drawing_model_is_backend_neutral() -> None:
    package = ROOT / "src" / "pywpdoc" / "core" / "drawing"
    forbidden_prefixes = (
        "pywpdoc.hwpx", "pywpdoc.docx",
        "pywpdoc._engine.hwpx", "pywpdoc._engine.docx",
        "docx", "lxml",
    )
    for path in package.rglob("*.py"):
        for imported in _imports(path):
            assert not imported.startswith(forbidden_prefixes), (path, imported)


def test_template_structure_planning_is_backend_neutral() -> None:
    package = ROOT / "src" / "pywpdoc" / "features" / "template" / "structure"
    forbidden_prefixes = (
        "pywpdoc.hwpx", "pywpdoc.docx",
        "pywpdoc._engine.hwpx", "pywpdoc._engine.docx",
        "docx", "lxml",
        "pywpdoc.features.find", "pywpdoc.features.replace",
    )
    for path in package.rglob("*.py"):
        for imported in _imports(path):
            assert not imported.startswith(forbidden_prefixes), (path, imported)


def test_runtime_package_does_not_depend_on_repository_quality_tools() -> None:
    package = ROOT / "src" / "pywpdoc"
    for path in package.rglob("*.py"):
        for imported in _imports(path):
            assert not imported.startswith("quality"), (path, imported)
