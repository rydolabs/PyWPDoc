from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import shlex
import sys
import zipfile

from lxml import etree

from pywpdoc import Document
from tests.quality.docx_package import validate_docx_package
from tests.quality.openxml_sdk import validate_with_openxml_sdk


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rewrite_zip(source: Path, target: Path, transform) -> None:
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(target, "w") as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            data = transform(info.filename, data)
            zout.writestr(info, data)


def test_generated_docx_passes_mandatory_opc_gate(tmp_path: Path) -> None:
    doc = Document.new("docx")
    doc.add_paragraph("quality gate")
    path = tmp_path / "valid.docx"
    doc.save(path)

    before = _sha(path)
    report = validate_docx_package(path)
    after = _sha(path)

    assert report.ok, report.issues
    assert before == after  # validation is strictly read-only


def test_opc_gate_detects_broken_internal_relationship(tmp_path: Path) -> None:
    doc = Document.new("docx")
    doc.add_paragraph("broken rel test")
    source = tmp_path / "source.docx"
    doc.save(source)
    broken = tmp_path / "broken.docx"

    rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"

    def transform(name: str, data: bytes) -> bytes:
        if name != "word/_rels/document.xml.rels":
            return data
        root = etree.fromstring(data)
        etree.SubElement(
            root,
            f"{{{rel_ns}}}Relationship",
            Id="rIdBroken",
            Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
            Target="media/does-not-exist.png",
        )
        return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)

    _rewrite_zip(source, broken, transform)
    report = validate_docx_package(broken)
    assert not report.ok
    assert any(issue.code == "opc-relationship-target-missing" for issue in report.issues)


def test_opc_gate_detects_malformed_xml(tmp_path: Path) -> None:
    doc = Document.new("docx")
    doc.add_paragraph("bad xml test")
    source = tmp_path / "source.docx"
    doc.save(source)
    broken = tmp_path / "bad-xml.docx"

    _rewrite_zip(
        source,
        broken,
        lambda name, data: b"<bad>" if name == "word/document.xml" else data,
    )
    report = validate_docx_package(broken)
    assert not report.ok
    assert any(issue.code == "opc-xml-invalid" for issue in report.issues)


def test_openxml_sdk_adapter_is_external_and_opt_in(tmp_path: Path, monkeypatch) -> None:
    doc = Document.new("docx")
    doc.add_paragraph("sdk adapter")
    path = tmp_path / "sdk.docx"
    doc.save(path)

    monkeypatch.delenv("PYWPDOC_OPENXML_VALIDATOR", raising=False)
    unavailable = validate_with_openxml_sdk(path)
    assert unavailable.available is False

    validator_dir = tmp_path / "validator with spaces"
    validator_dir.mkdir()
    validator = validator_dir / "validator.py"
    validator.write_text(
        "#!/usr/bin/env python3\nimport sys, zipfile\n"
        "zipfile.ZipFile(sys.argv[1]).testzip()\n"
        "print('validated')\n",
        encoding="utf-8",
    )
    validator.chmod(validator.stat().st_mode | stat.S_IXUSR)
    # Run through the current Python interpreter: Windows cannot execute a .py
    # file from a shebang alone, and the tempfile path may contain spaces.
    monkeypatch.setenv(
        "PYWPDOC_OPENXML_VALIDATOR",
        shlex.join([sys.executable, str(validator)]),
    )
    result = validate_with_openxml_sdk(path)
    assert result.available is True
    assert result.command[:2] == (sys.executable, str(validator))
    assert result.ok is True
    assert "validated" in result.stdout


def test_school_notice_conversion_passes_opc_gate_and_keeps_baseline_parts(tmp_path: Path) -> None:
    import json

    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "tests/baseline/v0215_manifest.json").read_text(encoding="utf-8"))
    source = root / manifest["source_fixture"]
    out = tmp_path / "school-notice.docx"

    Document.rebuild(source, format="docx", preserve_layout=True).save(out)
    report = validate_docx_package(out)
    assert report.ok, report.issues

    with zipfile.ZipFile(out) as zf:
        got = {
            name: hashlib.sha256(zf.read(name)).hexdigest()
            for name in manifest["docx_selected_parts"]
        }
    assert got == manifest["docx_selected_parts"]
