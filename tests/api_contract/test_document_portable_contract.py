"""Stable Common API methods are explicit and tested on both file types."""
from __future__ import annotations
import base64
import inspect
from pathlib import Path

import pytest
from pywpdoc import Document, DocumentValueError, DocumentUnsupportedError, Mm

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_document_explicit_core_surface(fmt: str, tmp_path: Path):
    for name in ("paragraphs", "tables", "sections", "pictures", "styles", "core_properties",
                 "add_paragraph", "add_table", "add_picture", "add_section", "save"):
        assert name in vars(Document), name
    document = Document.new(fmt)
    document.add_paragraph("Portable")
    document.add_table(1, 1).cell(0, 0).text = "A"
    dest = tmp_path / f"portable.{fmt}"
    document.save(dest)
    reopened = Document.open(dest)
    assert reopened.paragraphs[-1].text == "Portable"
    assert reopened.tables[0].cell(0, 0).text == "A"

@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_picture_signature_inference_and_units(fmt: str, tmp_path: Path):
    document = Document.new(fmt)
    pic = document.add_picture(PNG, width=Mm(25.4), height=Mm(12.7))
    assert abs(pic.width.mm - 25.4) < 0.05
    assert abs(pic.height.mm - 12.7) < 0.05
    path = tmp_path / f"image.{fmt}"
    document.save(path)
    assert Document.open(path).pictures

@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_picture_unknown_format_rejected_before_mutating(fmt):
    document = Document.new(fmt)
    with pytest.raises(DocumentValueError) as error:
        document.add_picture(b"not-an-image")
    assert error.value.code == "common-image-format-unknown"
    assert document.pictures == []

@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_add_section_has_small_portable_signature(fmt, tmp_path):
    document = Document.new(fmt)
    assert str(inspect.signature(document.add_section)) == "()"
    with pytest.raises(TypeError):
        document.add_section(after=0)
    with pytest.raises(TypeError):
        document.add_section(start_type=1)
    section = document.add_section()
    assert section is not None
    document.save(tmp_path / f"section.{fmt}")

@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_expert_object_and_wrong_format_guard(fmt):
    document = Document.new(fmt)
    assert document.unwrap() is document.native
    assert getattr(document, fmt) is document.native
    with pytest.raises(DocumentUnsupportedError):
        getattr(document, "hwpx" if fmt == "docx" else "docx")
