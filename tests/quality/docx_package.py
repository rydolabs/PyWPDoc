"""Mandatory lightweight DOCX/OPC package integrity gate.

This is intentionally repository tooling, not a replacement for the Microsoft
Open XML SDK schema validator.  It catches package corruption classes that are
valuable before an external schema validator/render smoke is run:

- ZIP corruption / duplicate parts
- malformed XML parts
- missing required package/document parts
- broken internal relationships
- duplicate relationship ids
- duplicate/missing content-type declarations
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
import posixpath
import zipfile

from lxml import etree

_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
_OFFICE_DOCUMENT_REL = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
)


@dataclass(frozen=True)
class PackageIssue:
    code: str
    message: str
    part: str | None = None


@dataclass
class PackageValidationReport:
    path: Path
    issues: list[PackageIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def add(self, code: str, message: str, part: str | None = None) -> None:
        self.issues.append(PackageIssue(code, message, part))


def _source_part_for_rels(rels_name: str) -> str:
    if rels_name == "_rels/.rels":
        return ""
    marker = "/_rels/"
    if marker not in rels_name or not rels_name.endswith(".rels"):
        return ""
    prefix, filename = rels_name.split(marker, 1)
    return f"{prefix}/{filename[:-5]}"


def _resolve_target(source_part: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    base = posixpath.dirname(source_part)
    return posixpath.normpath(posixpath.join(base, target)).lstrip("/")


def validate_docx_package(path: str | Path) -> PackageValidationReport:
    path = Path(path)
    report = PackageValidationReport(path=path)

    try:
        with zipfile.ZipFile(path) as zf:
            infos = zf.infolist()
            names = [info.filename for info in infos if not info.is_dir()]
            name_set = set(names)

            duplicates = sorted({name for name in names if names.count(name) > 1})
            for name in duplicates:
                report.add("opc-duplicate-part", f"duplicate package part: {name}", name)

            bad = zf.testzip()
            if bad:
                report.add("opc-zip-crc", f"ZIP CRC failure: {bad}", bad)

            for required in ("[Content_Types].xml", "_rels/.rels", "word/document.xml"):
                if required not in name_set:
                    report.add("opc-required-part-missing", f"required part missing: {required}", required)

            parsed: dict[str, etree._Element] = {}
            for name in names:
                if name.endswith(".xml") or name.endswith(".rels"):
                    try:
                        parsed[name] = etree.fromstring(zf.read(name))
                    except (etree.XMLSyntaxError, KeyError) as exc:
                        report.add("opc-xml-invalid", f"invalid XML: {exc}", name)

            content_types = parsed.get("[Content_Types].xml")
            defaults: dict[str, str] = {}
            overrides: dict[str, str] = {}
            if content_types is not None:
                if content_types.tag != f"{{{_CT_NS}}}Types":
                    report.add(
                        "opc-content-types-root",
                        "[Content_Types].xml has an unexpected root element",
                        "[Content_Types].xml",
                    )
                for node in content_types:
                    local = etree.QName(node).localname
                    if local == "Default":
                        ext = (node.get("Extension") or "").lower()
                        value = node.get("ContentType") or ""
                        if ext in defaults:
                            report.add(
                                "opc-content-type-duplicate-default",
                                f"duplicate Default content type for .{ext}",
                                "[Content_Types].xml",
                            )
                        defaults[ext] = value
                    elif local == "Override":
                        part_name = (node.get("PartName") or "").lstrip("/")
                        value = node.get("ContentType") or ""
                        if part_name in overrides:
                            report.add(
                                "opc-content-type-duplicate-override",
                                f"duplicate Override content type for {part_name}",
                                "[Content_Types].xml",
                            )
                        overrides[part_name] = value

                for name in names:
                    if name == "[Content_Types].xml":
                        continue
                    ext = ("rels" if name.endswith(".rels") else PurePosixPath(name).suffix.lstrip(".").lower())
                    if name not in overrides and ext not in defaults:
                        report.add(
                            "opc-content-type-missing",
                            f"no content type declaration for {name}",
                            name,
                        )

            for name, root in parsed.items():
                if not name.endswith(".rels"):
                    continue
                source_part = _source_part_for_rels(name)
                ids: set[str] = set()
                for rel in root.findall(f"{{{_REL_NS}}}Relationship"):
                    rel_id = rel.get("Id") or ""
                    if rel_id in ids:
                        report.add(
                            "opc-relationship-id-duplicate",
                            f"duplicate relationship id {rel_id!r}",
                            name,
                        )
                    ids.add(rel_id)
                    if rel.get("TargetMode") == "External":
                        continue
                    target = rel.get("Target") or ""
                    resolved = _resolve_target(source_part, target)
                    if resolved and resolved not in name_set:
                        report.add(
                            "opc-relationship-target-missing",
                            f"relationship target does not exist: {target} -> {resolved}",
                            name,
                        )

            root_rels = parsed.get("_rels/.rels")
            if root_rels is not None:
                office_targets = []
                for rel in root_rels.findall(f"{{{_REL_NS}}}Relationship"):
                    if rel.get("Type") == _OFFICE_DOCUMENT_REL:
                        office_targets.append(_resolve_target("", rel.get("Target") or ""))
                if not office_targets:
                    report.add(
                        "opc-office-document-rel-missing",
                        "package root has no officeDocument relationship",
                        "_rels/.rels",
                    )
                elif len(office_targets) > 1:
                    report.add(
                        "opc-office-document-rel-multiple",
                        "package root has multiple officeDocument relationships",
                        "_rels/.rels",
                    )

    except (zipfile.BadZipFile, OSError) as exc:
        report.add("opc-zip-invalid", f"cannot open DOCX package: {exc}")

    return report


__all__ = ["PackageIssue", "PackageValidationReport", "validate_docx_package"]
