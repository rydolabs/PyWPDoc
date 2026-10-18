from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterable
from zipfile import ZIP_STORED, ZipFile
from lxml import etree

from .model import local_name
from .styles import _container

if TYPE_CHECKING:
    from .document import Document


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    part: str | None = None
    severity: str = "error"

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "part": self.part,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]
    checks: tuple[str, ...]

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "warning")

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "checks": list(self.checks),
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def raise_for_errors(self) -> None:
        if self.errors:
            from .errors import HwpxValidationError
            details = "; ".join(f"{i.code}: {i.message}" for i in self.errors[:8])
            raise HwpxValidationError(f"HWPX validation failed: {details}", report=self)


def _id_set(container, child_name: str) -> set[str]:
    return {
        node.get("id") or ""
        for node in container.children
        if local_name(node.tag) == child_name and node.get("id") is not None
    }


def _dense_id_issue(container, child_name: str, start: int, label: str) -> ValidationIssue | None:
    ids: list[int] = []
    for node in container.children:
        if local_name(node.tag) != child_name:
            continue
        try:
            ids.append(int(node.get("id") or ""))
        except ValueError:
            return ValidationIssue("shared-id-nonnumeric", f"{label} contains a non-numeric id")
    expected = list(range(start, start + len(ids)))
    if ids != expected:
        return ValidationIssue(
            "shared-id-gap",
            f"{label} ids must remain dense for Hancom compatibility: got {ids[:20]}, expected {expected[:20]}",
            "Contents/header.xml",
        )
    return None


def validate_document_model(document: "Document") -> ValidationReport:
    """Validate invariants we rely on before emitting an HWPX package.

    This intentionally checks only contracts we have evidence for. It is not a
    speculative full-schema validator.
    """
    issues: list[ValidationIssue] = []
    checks = ["shared-id-density", "typed-id-references", "bullet-image-dependencies", "section-count"]

    header = document.header_model
    definitions: dict[str, set[str]] = {}
    specs = [
        ("charProperties", "charPr", 0, "charPr"),
        ("paraProperties", "paraPr", 0, "paraPr"),
        ("borderFills", "borderFill", 1, "borderFill"),
        ("styles", "style", 0, "style"),
        ("tabProperties", "tabPr", 0, "tabPr"),
    ]
    for container_name, child_name, first, label in specs:
        try:
            container = _container(header, container_name)
        except ValueError:
            issues.append(ValidationIssue("shared-container-missing", f"header is missing {container_name}", "Contents/header.xml"))
            continue
        definitions[label] = _id_set(container, child_name)
        issue = _dense_id_issue(container, child_name, first, label)
        if issue is not None:
            issues.append(issue)

    # Optional paragraph-heading resource collections. They are absent from
    # simple HWPX files but, when present, their ids are part of the ParaShape
    # dependency graph used by tracked comparison.
    for container_name, child_name, first, label in (
        ("numberings", "numbering", 1, "numbering"),
        ("bullets", "bullet", 1, "bullet"),
    ):
        try:
            container = _container(header, container_name)
        except ValueError:
            continue
        definitions[label] = _id_set(container, child_name)
        issue = _dense_id_issue(container, child_name, first, label)
        if issue is not None:
            issues.append(issue)

    # Character-format resource references in the header.  CharShape tracking
    # relies on these refs being valid after cross-document import/remap.
    try:
        fontfaces = _container(header, "fontfaces")
    except ValueError:
        fontfaces = None
        issues.append(ValidationIssue("shared-container-missing", "header is missing fontfaces", "Contents/header.xml"))
    font_ids_by_lang: dict[str, set[str]] = {}
    if fontfaces is not None:
        for block in fontfaces.children:
            if local_name(block.tag) != "fontface":
                continue
            lang = (block.get("lang") or "").upper()
            font_ids_by_lang[lang] = _id_set(block, "font")
            issue = _dense_id_issue(block, "font", 0, f"font[{lang}]")
            if issue is not None:
                issues.append(issue)

    if "charPr" in definitions:
        char_container = _container(header, "charProperties")
        font_attrs = {
            "hangul": "HANGUL", "latin": "LATIN", "hanja": "HANJA",
            "japanese": "JAPANESE", "other": "OTHER", "symbol": "SYMBOL", "user": "USER",
        }
        for cp in char_container.children:
            if local_name(cp.tag) != "charPr":
                continue
            border_ref = cp.get("borderFillIDRef")
            if border_ref is not None and "borderFill" in definitions and border_ref not in definitions["borderFill"]:
                issues.append(ValidationIssue(
                    "charpr-borderfill-ref-missing",
                    f"charPr {cp.get('id')} references missing borderFill {border_ref}",
                    "Contents/header.xml",
                ))
            font_ref = next((c for c in cp.children if local_name(c.tag) == "fontRef"), None)
            if font_ref is None:
                continue
            for attr, lang in font_attrs.items():
                ref = font_ref.get(attr)
                if ref is not None and ref not in font_ids_by_lang.get(lang, set()):
                    issues.append(ValidationIssue(
                        "charpr-font-ref-missing",
                        f"charPr {cp.get('id')} {attr}={ref} references missing {lang} font",
                        "Contents/header.xml",
                    ))

    # Shared-style references in the header.
    if "paraPr" in definitions and "tabPr" in definitions:
        para_container = _container(header, "paraProperties")
        for pp in para_container.children:
            if local_name(pp.tag) != "paraPr":
                continue
            ref = pp.get("tabPrIDRef")
            if ref is not None and ref not in definitions["tabPr"]:
                issues.append(ValidationIssue("tabpr-ref-missing", f"paraPr {pp.get('id')} references missing tabPr {ref}", "Contents/header.xml"))
            border = next((c for c in pp.children if local_name(c.tag) == "border"), None)
            border_ref = None if border is None else border.get("borderFillIDRef")
            if border_ref is not None and "borderFill" in definitions and border_ref not in definitions["borderFill"]:
                issues.append(ValidationIssue(
                    "parapr-borderfill-ref-missing",
                    f"paraPr {pp.get('id')} references missing borderFill {border_ref}",
                    "Contents/header.xml",
                ))
            heading = next((c for c in pp.children if local_name(c.tag) == "heading"), None)
            if heading is not None:
                htype = (heading.get("type") or "NONE").upper()
                href = heading.get("idRef") or "0"
                if href != "0" and htype in {"NUMBER", "OUTLINE"} and "numbering" in definitions and href not in definitions["numbering"]:
                    issues.append(ValidationIssue(
                        "parapr-numbering-ref-missing",
                        f"paraPr {pp.get('id')} references missing numbering {href}",
                        "Contents/header.xml",
                    ))
                if href != "0" and htype == "BULLET" and "bullet" in definitions and href not in definitions["bullet"]:
                    issues.append(ValidationIssue(
                        "parapr-bullet-ref-missing",
                        f"paraPr {pp.get('id')} references missing bullet {href}",
                        "Contents/header.xml",
                    ))

    # Numbering/bullet paraHead character-property references must remain valid
    # after ParaShape resource import. 4294967295 is Hancom's 'none' sentinel.
    for container_name, child_name in (("numberings", "numbering"), ("bullets", "bullet")):
        try:
            collection = _container(header, container_name)
        except ValueError:
            continue
        for definition in collection.children:
            if local_name(definition.tag) != child_name:
                continue
            for head in definition.children:
                if local_name(head.tag) != "paraHead":
                    continue
                ref = head.get("charPrIDRef")
                if ref not in (None, "", "4294967295", "-1") and "charPr" in definitions and ref not in definitions["charPr"]:
                    issues.append(ValidationIssue(
                        "parahead-charpr-ref-missing",
                        f"{child_name} {definition.get('id')} paraHead references missing charPr {ref}",
                        "Contents/header.xml",
                    ))

    # Image bullets are header resources whose payload lives in BinData and is
    # addressed indirectly through the OPF manifest. Cross-document ParaShape
    # tracking can import these resources, so validate the full chain rather
    # than accepting a structurally present <img> with a dangling id.
    try:
        bullets = _container(header, "bullets")
    except ValueError:
        bullets = None
    manifest = next((node for node in document.content_model.iter() if local_name(node.tag) == "manifest"), None)
    manifest_items = {}
    if manifest is not None:
        manifest_items = {
            child.get("id") or "": child
            for child in manifest.children
            if local_name(child.tag) == "item" and child.get("id") is not None
        }
    if bullets is not None:
        for bullet in bullets.children:
            if local_name(bullet.tag) != "bullet":
                continue
            image_nodes = [child for child in bullet.children if local_name(child.tag) == "img"]
            uses_image = (bullet.get("useImage") or "0").strip().lower() in {"1", "true"} or bool(image_nodes)
            if not uses_image:
                continue
            if not image_nodes:
                issues.append(ValidationIssue(
                    "bullet-image-node-missing",
                    f"bullet {bullet.get('id')} uses an image but has no img child",
                    "Contents/header.xml",
                ))
                continue
            for img in image_nodes:
                ref = img.get("binaryItemIDRef")
                if not ref:
                    issues.append(ValidationIssue(
                        "bullet-image-ref-missing",
                        f"bullet {bullet.get('id')} image has no binaryItemIDRef",
                        "Contents/header.xml",
                    ))
                    continue
                item = manifest_items.get(ref)
                if item is None:
                    issues.append(ValidationIssue(
                        "bullet-image-manifest-ref-missing",
                        f"bullet {bullet.get('id')} references missing manifest item {ref}",
                        "Contents/header.xml",
                    ))
                    continue
                href = item.get("href") or ""
                if not href or href not in document._package.parts:
                    issues.append(ValidationIssue(
                        "bullet-image-payload-missing",
                        f"bullet {bullet.get('id')} manifest item {ref} has missing payload {href!r}",
                        href or "Contents/content.hpf",
                    ))
                media_type = (item.get("media-type") or "").lower()
                if media_type and not media_type.startswith("image/"):
                    issues.append(ValidationIssue(
                        "bullet-image-media-type-invalid",
                        f"bullet {bullet.get('id')} manifest item {ref} uses non-image media type {media_type}",
                        "Contents/content.hpf",
                    ))

    if "style" in definitions:
        styles = _container(header, "styles")
        for style in styles.children:
            if local_name(style.tag) != "style":
                continue
            for attr, key in (("charPrIDRef", "charPr"), ("paraPrIDRef", "paraPr"), ("nextStyleIDRef", "style")):
                ref = style.get(attr)
                if ref is not None and key in definitions and ref not in definitions[key]:
                    issues.append(ValidationIssue("style-ref-missing", f"style {style.get('id')} {attr}={ref} is missing", "Contents/header.xml"))

    # References from section content. 4294967295 is Hancom's common 'none'
    # sentinel for char references in numbering-related contexts, but normal
    # hp:run references must resolve to an actual charPr.
    for section_index, section in enumerate(document.section_models):
        part = f"Contents/section{section_index}.xml"
        for node in section.iter():
            lname = local_name(node.tag)
            if lname == "run":
                ref = node.get("charPrIDRef")
                if ref is not None and "charPr" in definitions and ref not in definitions["charPr"]:
                    issues.append(ValidationIssue("charpr-ref-missing", f"run references missing charPr {ref}", part))
            elif lname == "p":
                for attr, key in (("paraPrIDRef", "paraPr"), ("styleIDRef", "style")):
                    ref = node.get(attr)
                    if ref is not None and key in definitions and ref not in definitions[key]:
                        issues.append(ValidationIssue(f"{key.lower()}-ref-missing", f"paragraph {attr}={ref} is missing", part))
            elif lname in {"tc", "tbl"}:
                ref = node.get("borderFillIDRef")
                if ref is not None and "borderFill" in definitions and ref not in definitions["borderFill"]:
                    issues.append(ValidationIssue("borderfill-ref-missing", f"{lname} references missing borderFill {ref}", part))

    sec_cnt = document.header_model.get("secCnt")
    if sec_cnt is not None and sec_cnt != str(len(document.section_models)):
        issues.append(ValidationIssue("section-count-mismatch", f"header secCnt={sec_cnt}, models={len(document.section_models)}", "Contents/header.xml"))

    return ValidationReport(tuple(issues), tuple(checks))


def validate_hwpx_file(path: str | Path) -> ValidationReport:
    """Validate the emitted ZIP/package and reopen it through the public reader."""
    path = Path(path)
    issues: list[ValidationIssue] = []
    checks = ["zip-integrity", "mimetype", "required-parts", "xml-well-formed", "public-reopen", "model-invariants"]
    required = {"mimetype", "Contents/header.xml", "Contents/content.hpf", "Contents/section0.xml"}
    try:
        with ZipFile(path) as zf:
            bad = zf.testzip()
            if bad is not None:
                issues.append(ValidationIssue("zip-crc", f"CRC failure in {bad}"))
            names = zf.namelist()
            if not names or names[0] != "mimetype":
                issues.append(ValidationIssue("mimetype-order", "mimetype must be the first ZIP entry"))
            else:
                info = zf.getinfo("mimetype")
                if info.compress_type != ZIP_STORED:
                    issues.append(ValidationIssue("mimetype-compression", "mimetype must use STORE compression"))
                if zf.read("mimetype") != b"application/hwp+zip":
                    issues.append(ValidationIssue("mimetype-value", "unexpected mimetype payload"))
            missing = sorted(required - set(names))
            if missing:
                issues.append(ValidationIssue("required-part-missing", f"missing required parts: {missing}"))
            for name in names:
                if name.endswith((".xml", ".hpf", ".rdf")):
                    try:
                        etree.fromstring(zf.read(name), etree.XMLParser(remove_blank_text=False, recover=False))
                    except Exception as exc:
                        issues.append(ValidationIssue("xml-not-well-formed", str(exc), name))
    except Exception as exc:
        return ValidationReport((ValidationIssue("zip-open-failed", str(exc)),), tuple(checks))

    if not issues:
        try:
            from .document import Document
            reopened = Document.open(path)
            model_report = validate_document_model(reopened)
            issues.extend(model_report.issues)
        except Exception as exc:
            issues.append(ValidationIssue("public-reopen-failed", str(exc)))
    return ValidationReport(tuple(issues), tuple(checks))
