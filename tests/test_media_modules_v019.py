"""v0.19 picture/media module isolation and backend-owned contract tests."""
from __future__ import annotations

import ast
import base64
from pathlib import Path
import zipfile

import pytest

from pywpdoc._engine.core import Mm
from pywpdoc._engine.core.contracts import PictureBackend
from pywpdoc._engine.core.errors import DocumentUnsupportedError

ROOT = Path(__file__).resolve().parents[1] / "src" / "pywpdoc" / "_engine"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


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
def test_media_module_has_narrow_dependencies(kind: str):
    media = ROOT / kind / "media.py"
    assert media.exists()
    imports = _imports(media)
    opposite = f".{('docx' if kind == 'hwpx' else 'hwpx')}"
    assert ".backend" not in imports
    assert not [name for name in imports if ".common" in name or opposite in name]


def test_backend_facades_delegate_picture_implementation_to_media_modules():
    for kind in ("hwpx", "docx"):
        source = (ROOT / kind / "backend.py").read_text(encoding="utf-8")
        assert "class Picture(" not in source
        assert "from .media import Picture" in source


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_picture_public_type_is_backend_owned(kind: str):
    Document = _backend_class(kind)
    doc = Document.new()
    pic = doc.add_picture(PNG, "png", width=Mm(25.4), height=Mm(12.7))
    assert type(pic).__module__ == f"pywpdoc._engine.{kind}.media"
    assert isinstance(pic, PictureBackend)
    assert type(doc.pictures[-1]) is type(pic)


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_picture_size_resize_and_reopen(kind: str, tmp_path: Path):
    Document = _backend_class(kind)
    doc = Document.new()
    pic = doc.add_picture(PNG, "png", width=Mm(25.4), height=Mm(12.7))
    assert abs(pic.width.mm - 25.4) <= 0.03
    assert abs(pic.height.mm - 12.7) <= 0.03

    returned = pic.resize(width=Mm(30), height=Mm(15))
    assert returned is pic
    assert abs(pic.size[0].mm - 30.0) <= 0.03
    assert abs(pic.size[1].mm - 15.0) <= 0.03

    path = tmp_path / f"picture.{kind}"
    doc.save(path)
    reopened = Document.open(path)
    rp = reopened.pictures[-1]
    assert type(rp).__module__ == f"pywpdoc._engine.{kind}.media"
    assert abs(rp.width.mm - 30.0) <= 0.03
    assert abs(rp.height.mm - 15.0) <= 0.03


@pytest.mark.parametrize("kind", ["hwpx", "docx"])
def test_picture_binary_is_embedded_in_package(kind: str, tmp_path: Path):
    Document = _backend_class(kind)
    doc = Document.new()
    doc.add_picture(PNG, "png", width=Mm(10), height=Mm(10))
    path = tmp_path / f"embedded.{kind}"
    doc.save(path)
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        if kind == "hwpx":
            media = [name for name in names if name.startswith("BinData/") and name.endswith(".png")]
        else:
            media = [name for name in names if name.startswith("word/media/") and name.endswith(".png")]
        assert media
        assert PNG in [zf.read(name) for name in media]


def test_common_returns_backend_owned_picture_types():
    from pywpdoc._engine.common import Document as CommonDocument

    for kind in ("hwpx", "docx"):
        direct = _backend_class(kind).new()
        common = CommonDocument.new(kind)
        direct_pic = direct.add_picture(PNG, "png", width=Mm(10), height=Mm(10))
        common_pic = common.add_picture(PNG, "png", width=Mm(10), height=Mm(10))
        assert type(common_pic) is type(direct_pic)
        assert type(common.pictures[-1]) is type(direct_pic)
        assert ".common" not in type(common_pic).__module__


def test_docx_floating_picture_fails_closed_in_backend_media_module():
    from pywpdoc._engine.docx import Document

    doc = Document.new()
    with pytest.raises(DocumentUnsupportedError) as exc_info:
        doc.add_picture(PNG, "png", width=Mm(10), height=Mm(10), treat_as_char=False)
    assert exc_info.value.code == "docx-floating-picture-unsupported"
