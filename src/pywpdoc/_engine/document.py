from __future__ import annotations

from pathlib import Path
from typing import Any
from lxml import etree
import base64
import json
import random
import re
import os
import tempfile

from .model import (
    ElementModel, Paragraph, Table, Rectangle, Picture, Section, Hyperlink,
    HP, HH, local_name,
)
from .package import HwpxPackage, PackageEntryInfo
from .styles import Styles
from .errors import HwpxValueError


XML_SUFFIXES = (".xml", ".hpf", ".rdf")
OPF_NS = "http://www.idpf.org/2007/opf/"
OPF = f"{{{OPF_NS}}}"
_SECTION_RE = re.compile(r"^Contents/section(\d+)\.xml$")


def _xml_bytes(model: ElementModel) -> bytes:
    root = model.to_element(root=True)
    return etree.tostring(
        root, encoding="UTF-8", xml_declaration=True, standalone=True, pretty_print=False
    )


def _parse_xml(raw: bytes) -> ElementModel:
    parser = etree.XMLParser(remove_blank_text=False, remove_comments=False, remove_pis=False)
    return ElementModel.from_element(etree.fromstring(raw, parser), root=True)


def _next_para_id() -> str:
    return str(random.SystemRandom().randrange(1, 2**31 - 1))


def _clone(model: ElementModel) -> ElementModel:
    return ElementModel.from_dict(model.to_dict())


def _section_part_sort_key(name: str) -> tuple[int, str]:
    match = _SECTION_RE.match(name)
    return (int(match.group(1)) if match else 10**9, name)


class Document:
    """python-docx-shaped HWPX document object.

    HWPX stores each section in a separate XML part.  ``Document`` therefore
    owns a list of section models and synchronizes that list with ``content.hpf``
    and the ZIP package at save time.  Known semantics are exposed through
    typed proxies; unknown XML stays lossless in :class:`ElementModel`.
    """

    def __init__(self, package: HwpxPackage):
        self._package = package
        self._manifest: dict[str, Any] | None = None
        self._base_dir: Path | None = None
        self.header_model = _parse_xml(package.parts["Contents/header.xml"])
        self.content_model = _parse_xml(package.parts["Contents/content.hpf"])

        section_names = sorted(
            (name for name in package.parts if _SECTION_RE.match(name)),
            key=_section_part_sort_key,
        )
        if not section_names:
            raise ValueError("HWPX has no Contents/section*.xml part")
        self.section_models = [_parse_xml(package.parts[name]) for name in section_names]
        self._section_part_names = list(section_names)
        self._section_infos = [package.infos[name] for name in section_names]
        self.styles = Styles(self)
        self._capture_baselines()

    def _capture_baselines(self) -> None:
        """Snapshot parsed XML models so untouched package parts stay byte-exact.

        HWPX preservation is strongest when editing one semantic part does not
        cause unrelated XML parts to be reserialized. These snapshots are
        model-level (not byte-level): when a model is unchanged, the original
        package bytes remain in :class:`HwpxPackage` and are emitted verbatim.
        """
        self._baseline_header_model = self.header_model.to_dict()
        self._baseline_content_model = self.content_model.to_dict()
        self._baseline_section_models = [model.to_dict() for model in self.section_models]

    @staticmethod
    def _model_differs(model: ElementModel, baseline: dict | None) -> bool:
        return baseline is None or model.to_dict() != baseline

    @property
    def section_model(self) -> ElementModel:
        """Backward-compatible alias for the first section model."""
        return self.section_models[0]

    @section_model.setter
    def section_model(self, value: ElementModel) -> None:
        if self.section_models:
            self.section_models[0] = value
        else:
            self.section_models = [value]

    @classmethod
    def open(cls, source: str | Path) -> "Document":
        return cls(HwpxPackage.open(source))

    @classmethod
    def new(cls, *, compatibility: str = "hancom2020") -> "Document":
        """Create a blank HWPX document for the requested Hancom compatibility profile.

        ``hancom2020`` is the safe default and is based on a real Hancom 2020
        authored HWPX skeleton (OWPML 5.1.0.1 / xmlVersion 1.2). ``latest``
        keeps the previous 13.x skeleton for callers that explicitly want it.
        Existing documents opened with :meth:`open` retain their original
        ``version.xml`` bytes unless that part is explicitly replaced.
        """
        profile = str(compatibility).strip().lower().replace("_", "").replace("-", "")
        if profile in {"hancom2020", "hwp2020", "2020"}:
            filename = "default_2020.hwpx"
        elif profile in {"latest", "hancom2024", "hwp2024", "2024"}:
            filename = "default.hwpx"
        else:
            raise HwpxValueError(
                "unsupported HWPX compatibility profile",
                code="hwpx-compatibility-profile-invalid",
                context={"compatibility": compatibility},
                suggestion="Use 'hancom2020' or 'latest'.",
            )
        default_template = Path(__file__).with_name("data") / filename
        return cls(HwpxPackage.open(default_template))

    @classmethod
    def from_reverse_model(
        cls,
        model_path: str | Path,
        *,
        default_template: str | Path | None = None,
    ) -> "Document":
        model_path = Path(model_path)
        manifest = json.loads(model_path.read_text(encoding="utf-8"))
        if default_template is None:
            default_template = Path(__file__).with_name("data") / "default.hwpx"
        package = HwpxPackage.open(default_template)
        self = cls(package)
        self._manifest = manifest
        self._base_dir = model_path.parent

        document_data = manifest["document"]
        if "sections" in document_data:
            self.section_models = [
                ElementModel.from_dict(item["model"]) for item in document_data["sections"]
            ]
        else:  # v0.3 reverse model compatibility
            self.section_models = [ElementModel.from_dict(document_data["section"]["model"])]
        self.header_model = ElementModel.from_dict(document_data["header"]["model"])
        self._install_package_entries()
        self.content_model = _parse_xml(self._package.parts["Contents/content.hpf"])
        self._section_part_names = [f"Contents/section{i}.xml" for i in range(len(self.section_models))]
        self._section_infos = [
            self._package.infos.get(name, self._package.infos.get("Contents/section0.xml"))
            for name in self._section_part_names
        ]
        self._capture_baselines()
        return self

    @property
    def element_model(self) -> ElementModel:
        """OXML escape hatch for the first section root."""
        return self.section_model

    @property
    def sections(self) -> list[Section]:
        return [Section(model, self) for model in self.section_models]

    @property
    def page_setup(self):
        return self.sections[0].page_setup

    @property
    def core_properties(self):
        from .metadata import CoreProperties
        return CoreProperties(self)

    @property
    def settings(self):
        from .metadata import Settings
        cached = getattr(self, "_settings_proxy", None)
        if cached is None:
            cached = self._settings_proxy = Settings(self)
        return cached

    @property
    def paragraphs(self) -> list[Paragraph]:
        """Top-level user paragraphs, matching python-docx semantics.

        HWPX-only carrier paragraphs that contain only ``secPr``/section-start
        controls and table-only wrapper paragraphs are hidden here. Use
        :attr:`all_paragraphs` or ``Section.paragraphs`` for format-level access.
        """
        return [item for item in self.iter_inner_content() if isinstance(item, Paragraph)]

    @property
    def all_paragraphs(self) -> list[Paragraph]:
        return [
            Paragraph(n, self)
            for section in self.section_models
            for n in section.iter()
            if local_name(n.tag) == "p"
        ]

    @property
    def tables(self) -> list[Table]:
        """Top-level body tables, matching python-docx ``Document.tables``.

        HWPX can nest tables inside cells, shapes, headers, and footers. Those
        are intentionally excluded here; use :attr:`all_tables` for recursive
        format-level traversal.
        """
        return [item for item in self.iter_inner_content() if isinstance(item, Table)]

    @property
    def all_tables(self) -> list[Table]:
        """All semantic table objects recursively, including nested stories.

        Header/footer logical stories are mirrored into body controls. Mirrored
        copies carry the same table id, so this recursive escape hatch dedupes
        them by table id within each section while preserving first occurrence.
        """
        result: list[Table] = []
        for section_index, section in enumerate(self.section_models):
            seen: set[tuple[int, str]] = set()
            for node in section.iter():
                if local_name(node.tag) != "tbl":
                    continue
                table_id = node.get("id")
                key = (section_index, table_id) if table_id else (section_index, f"obj:{id(node)}")
                if key in seen:
                    continue
                seen.add(key)
                result.append(Table(node, self))
        return result

    def iter_inner_content(self):
        """Yield top-level Paragraph and Table objects in document order.

        HWPX stores a table inside a paragraph/run rather than as a sibling of
        paragraphs. For a table-only wrapper paragraph (the shape produced by
        ``add_table``), this method yields the table instead of the wrapper so
        callers get the same block-level mental model as python-docx. Mixed
        paragraphs remain Paragraph objects because HWPX can legally contain
        richer inline content than DOCX block traversal can represent.
        """
        for section_model in self.section_models:
            for node in section_model.children:
                if local_name(node.tag) != "p":
                    continue
                paragraph = Paragraph(node, self)
                direct_tables = [
                    child
                    for run in node.children if local_name(run.tag) == "run"
                    for child in run.children if local_name(child.tag) == "tbl"
                ]
                visible_text = paragraph.text
                non_table_content = False
                for run in node.children:
                    if local_name(run.tag) != "run":
                        continue
                    for child in run.children:
                        lname = local_name(child.tag)
                        if lname in {"tbl", "secPr"}:
                            continue
                        if lname == "t" and not paragraph.text:
                            continue
                        if lname == "ctrl" and any(local_name(x.tag) in {"colPr", "header", "footer", "pageNum", "pageNumCtrl", "pageHiding", "newNum"} for x in child.children):
                            continue
                        if lname == "t" and not (child.text or child.children):
                            continue
                        non_table_content = True
                has_section_setup = any(local_name(x.tag) == "secPr" for x in node.iter())
                if direct_tables and not visible_text and not non_table_content:
                    for table in direct_tables:
                        yield Table(table, self)
                elif has_section_setup and not visible_text and not non_table_content:
                    # HWPX needs a carrier paragraph for secPr; DOCX has sectPr
                    # as a block sibling. Hide that implementation detail here.
                    continue
                else:
                    yield paragraph

    @property
    def rectangles(self) -> list[Rectangle]:
        return [
            Rectangle(n, self)
            for section in self.section_models
            for n in section.iter()
            if local_name(n.tag) == "rect"
        ]

    @property
    def pictures(self) -> list[Picture]:
        return [
            Picture(n, self)
            for section in self.section_models
            for n in section.iter()
            if local_name(n.tag) == "pic"
        ]

    def _resolve_section_model(self, section: Section | int | None) -> ElementModel:
        if section is None:
            return self.section_models[-1]
        if isinstance(section, int):
            return self.section_models[section]
        if isinstance(section, Section):
            if section.document is not self:
                raise ValueError("section belongs to another document")
            return section.element_model
        raise TypeError("section must be a Section, index, or None")

    def _section_index_for_model(self, model: ElementModel) -> int:
        for index, candidate in enumerate(self.section_models):
            if candidate is model:
                return index
        raise ValueError("section model is not attached to this document")

    def section_for_descendant(self, target: ElementModel) -> Section | None:
        for section in self.sections:
            if any(node is target for node in section.element_model.iter()):
                return section
        return None

    def add_paragraph(
        self,
        text: str = "",
        style=None,
        *,
        section: Section | int | None = None,
        para_pr_id_ref: str | int = "0",
        style_id_ref: str | int = "0",
        char_pr_id_ref: str | int = "0",
        include_run: bool = True,
    ) -> Paragraph:
        if style is not None:
            style_obj = self.styles.resolve(style)
            if (style_obj.type or "").upper() not in {"PARA", "PARAGRAPH"}:
                raise ValueError("paragraph style must be a paragraph style")
            style_id_ref = style_obj.id
            para_pr_id_ref = style_obj.para_pr_id_ref or para_pr_id_ref
            char_pr_id_ref = style_obj.char_pr_id_ref or char_pr_id_ref
        p = ElementModel(
            HP + "p",
            attrs=[
                ("id", _next_para_id()),
                ("paraPrIDRef", str(para_pr_id_ref)),
                ("styleIDRef", str(style_id_ref)),
                ("pageBreak", "0"),
                ("columnBreak", "0"),
                ("merged", "0"),
            ],
        )
        paragraph = Paragraph(p, self)
        if include_run:
            paragraph.add_run(text, char_pr_id_ref=char_pr_id_ref)
        self._resolve_section_model(section).children.append(p)
        return paragraph

    def add_heading(self, text: str = "", level: int = 1, *, section: Section | int | None = None) -> Paragraph:
        """Add an outline heading using the skeleton's native Outline 1..10 styles."""
        if not 1 <= int(level) <= 10:
            raise ValueError("level must be between 1 and 10")
        style = self.styles.get(f"Outline {int(level)}") or self.styles.get(f"개요 {int(level)}")
        if style is None:
            raise KeyError(f"heading style for level {level} is unavailable")
        p=self.add_paragraph(text, section=section, para_pr_id_ref=style.para_pr_id_ref or "0", style_id_ref=style.id, char_pr_id_ref=style.char_pr_id_ref or "0")
        return p

    def add_page_break(self, *, section: Section | int | None = None) -> Paragraph:
        p=self.add_paragraph("", section=section); p.page_break=True; return p

    def add_table(
        self, rows: int, cols: int, style=None, *, section: Section | int | None = None,
        width: int | None = None, height: int | None = None,
        border_fill_id_ref: str | int | None = None,
    ) -> Table:
        paragraph = self.add_paragraph(include_run=False, section=section)
        table = paragraph.add_table(rows, cols, width=width, height=height, border_fill_id_ref=border_fill_id_ref)
        if style is not None:
            table.style = style
        return table

    def add_rectangle(
        self, width: int = 14400, height: int = 7200, *, section: Section | int | None = None,
        text: str | None = None, line_color: str = "#000000", line_width: str = "33",
        fill_color: str | None = None, treat_as_char: bool = True,
    ) -> Rectangle:
        paragraph = self.add_paragraph(include_run=False, section=section)
        return paragraph.add_rectangle(
            width, height, text=text, line_color=line_color, line_width=line_width,
            fill_color=fill_color, treat_as_char=treat_as_char,
        )

    def add_picture(
        self, image_data: bytes, image_format: str, *, section: Section | int | None = None,
        width: int = 14400, height: int | None = None, treat_as_char: bool = True,
    ) -> Picture:
        from .authoring import add_binary_image
        item_id = add_binary_image(self, image_data, image_format)
        if height is None:
            height = width
            if image_format.lower().lstrip(".") == "png" and len(image_data) >= 24 and image_data.startswith(b"\x89PNG\r\n\x1a\n"):
                sw = int.from_bytes(image_data[16:20], "big")
                sh = int.from_bytes(image_data[20:24], "big")
                if sw > 0 and sh > 0:
                    height = round(width * sh / sw)
        paragraph = self.add_paragraph(include_run=False, section=section)
        return paragraph.add_picture(item_id, width=width, height=height, treat_as_char=treat_as_char)

    def _empty_section_from(self, source: ElementModel) -> ElementModel:
        """Clone layout-bearing section properties while discarding story/body content."""
        root = _clone(source)
        source_first = next((c for c in root.children if local_name(c.tag) == "p"), None)
        if source_first is None:
            from .authoring import paragraph_attrs
            source_first = ElementModel(HP + "p", attrs=paragraph_attrs())

        # Find and clone the section properties; strip section-specific stories.
        sec_pr = next((n for n in source_first.iter() if local_name(n.tag) == "secPr"), None)
        if sec_pr is None:
            sec_pr = next((n for n in root.iter() if local_name(n.tag) == "secPr"), None)
        if sec_pr is not None:
            sec_pr = _clone(sec_pr)
            sec_pr.children[:] = [
                c for c in sec_pr.children
                if local_name(c.tag) not in {"header", "footer", "headerApply", "footerApply"}
            ]

        # Preserve the column definition when present.
        col_pr = next((n for n in source_first.iter() if local_name(n.tag) == "colPr"), None)
        if col_pr is not None:
            col_pr = _clone(col_pr)

        p = ElementModel(
            HP + "p",
            attrs=[
                ("id", _next_para_id()), ("paraPrIDRef", "0"), ("styleIDRef", "0"),
                ("pageBreak", "0"), ("columnBreak", "0"), ("merged", "0"),
            ],
        )
        control_run = ElementModel(HP + "run", attrs=[("charPrIDRef", "0")])
        if sec_pr is not None:
            control_run.children.append(sec_pr)
        if col_pr is not None:
            ctrl = ElementModel(HP + "ctrl")
            ctrl.children.append(col_pr)
            control_run.children.append(ctrl)
        p.children.append(control_run)
        text_run = ElementModel(HP + "run", attrs=[("charPrIDRef", "0")])
        text_run.children.append(ElementModel(HP + "t", text=""))
        p.children.append(text_run)
        root.children = [p]
        return root

    def add_section(self, *, after: int | None = None) -> Section:
        """Create a new empty section and return it.

        Page geometry and note/page-border settings are cloned from the nearest
        existing section, while body content and header/footer stories are not.
        The package manifest/spine and ``header@secCnt`` are synchronized on save.
        """
        if not self.section_models:
            raise ValueError("document has no source section layout")
        if after is None:
            insert_at = len(self.section_models)
            source_index = len(self.section_models) - 1
        else:
            if after < -1 or after >= len(self.section_models):
                raise IndexError(after)
            insert_at = after + 1
            source_index = max(0, min(after, len(self.section_models) - 1))
        model = self._empty_section_from(self.section_models[source_index])
        self.section_models.insert(insert_at, model)
        source_info = self._section_infos[source_index] if self._section_infos else self._package.infos.get("Contents/section0.xml")
        self._section_infos.insert(insert_at, source_info)
        self._section_part_names.insert(insert_at, f"Contents/section{insert_at}.xml")
        return Section(model, self)

    def remove_section(self, section: Section | int) -> None:
        if len(self.section_models) <= 1:
            raise ValueError("document must contain at least one section")
        if isinstance(section, int):
            index = section
        else:
            index = self._section_index_for_model(section.element_model)
        del self.section_models[index]
        if index < len(self._section_infos):
            del self._section_infos[index]
        if index < len(self._section_part_names):
            del self._section_part_names[index]

    def add_list_paragraph(
        self, text: str, *, kind: str = "bullet", level: int = 0,
        levels: list[dict[str, str]] | None = None, section: Section | int | None = None,
        restart: bool = False, start: int | None = None,
    ) -> Paragraph:
        if level < 0:
            raise ValueError("level must be non-negative")
        specs = [dict(item) for item in (levels or [{} for _ in range(level + 1)])]
        while len(specs) <= level:
            specs.append({})
        if start is not None:
            if int(start) < 1:
                raise ValueError("list start must be >= 1")
            specs[level]["start"] = str(int(start))
        refs = self.styles.ensure_numbering(kind=kind, levels=specs, restart=restart)
        if level >= len(refs):
            raise ValueError("level is out of range for the numbering definition")
        return self.add_paragraph(text, section=section, para_pr_id_ref=refs[level])

    def add_bookmark(
        self, name: str, *, paragraph: Paragraph | None = None,
        section: Section | int | None = None,
    ) -> ElementModel:
        target = paragraph or self.add_paragraph("", section=section)
        if target.document is not self:
            raise ValueError("paragraph belongs to another document")
        return target.add_bookmark(name)

    def add_hyperlink(
        self, url: str, display_text: str, *, paragraph: Paragraph | None = None,
        section: Section | int | None = None, char_pr_id_ref: str | int | None = None,
    ) -> Hyperlink:
        target = paragraph or self.add_paragraph("", section=section)
        if target.document is not self:
            raise ValueError("paragraph belongs to another document")
        return target.add_hyperlink(url, display_text, char_pr_id_ref=char_pr_id_ref)

    def _replace_paragraphs(self, *, everywhere: bool) -> list[Paragraph]:
        if not everywhere:
            return self.paragraphs

        result: list[Paragraph] = []
        seen_nodes: set[int] = set()

        def story_key(node: ElementModel) -> tuple[str, str, str | None]:
            return (
                local_name(node.tag),
                node.get("applyPageType", "BOTH") or "BOTH",
                node.get("id"),
            )

        for section in self.section_models:
            # Hancom can legitimately reuse paragraph ids (notably ``id=0``)
            # for unrelated table-cell paragraphs, so paragraph @id is not an
            # identity key.  Deduplicate only the header/footer control mirrors
            # that PyWPDoc/Hancom keep alongside logical secPr stories.
            logical_story_keys: set[tuple[str, str, str | None]] = set()
            for node in section.iter():
                if local_name(node.tag) != "secPr":
                    continue
                for child in node.children:
                    if local_name(child.tag) in {"header", "footer"}:
                        logical_story_keys.add(story_key(child))

            def walk(
                node: ElementModel, *, inside_ctrl: bool = False, blocked: bool = False
            ) -> None:
                lname = local_name(node.tag)
                blocked = (
                    blocked
                    or lname in {"memo", "memogroup"}
                    or (lname == "fieldBegin" and (node.get("type", "") or "").upper() == "MEMO")
                )
                if blocked:
                    return

                # A logical header/footer under secPr is mirrored under hp:ctrl.
                # Skip only that semantic mirror; never use paragraph @id for
                # general deduplication because real Hancom files may repeat it.
                if inside_ctrl and lname in {"header", "footer"} and story_key(node) in logical_story_keys:
                    return

                if lname == "p":
                    marker = id(node)
                    if marker not in seen_nodes:
                        seen_nodes.add(marker)
                        result.append(Paragraph(node, self))

                child_inside_ctrl = inside_ctrl or lname == "ctrl"
                for child in node.children:
                    walk(child, inside_ctrl=child_inside_ctrl, blocked=blocked)

            walk(section)

        return result

    def replace(self, search: str, replacement: str, *, everywhere: bool = True, count: int = -1) -> int:
        """Structure-preserving visible-text replacement.

        ``everywhere=True`` includes body, tables, shapes, headers/footers and
        notes while deduplicating Hancom header/footer mirror stories. Memo
        bodies are intentionally excluded, matching the preservation-first
        contract used for comments/annotations. Set ``everywhere=False`` to
        restrict replacement to top-level body paragraphs. Matches spanning
        run and hyperlink boundaries are supported by :meth:`Paragraph.replace`.
        """
        if not search:
            raise HwpxValueError("search must not be empty", code="text-search-empty")
        if count == 0:
            return 0
        remaining = None if count is None or int(count) < 0 else int(count)
        changed = 0
        for paragraph in self._replace_paragraphs(everywhere=everywhere):
            if remaining is not None and remaining <= 0:
                break
            n = paragraph.replace(search, replacement, -1 if remaining is None else remaining)
            changed += n
            if remaining is not None:
                remaining -= n
        return changed

    def replace_text(self, search: str, replacement: str) -> int:
        """Legacy raw text-node replacement retained for backwards compatibility.

        New code should use :meth:`replace`, which can span runs and preserves
        semantic stories while avoiding mirrored-header double edits.
        """
        if not search:
            raise ValueError("search must not be empty")
        count = 0
        for section in self.section_models:
            for node in section.iter():
                if local_name(node.tag) == "t" and node.text and search in node.text:
                    count += node.text.count(search)
                    node.text = node.text.replace(search, replacement)
        return count

    def _install_package_entries(self) -> None:
        assert self._manifest is not None and self._base_dir is not None
        entries = self._manifest["package"]["entries"]
        order: list[str] = []
        section_cursor = 0
        for item in entries:
            name = item["name"]
            order.append(name)
            meta = PackageEntryInfo(
                name=name,
                compress_type=item["compress_type"],
                date_time=tuple(item["date_time"]),
                comment=base64.b64decode(item.get("comment_b64", "")),
                extra=base64.b64decode(item.get("extra_b64", "")),
                internal_attr=item.get("internal_attr", 0),
                external_attr=item.get("external_attr", 0),
                create_system=item.get("create_system", 3),
                create_version=item.get("create_version", 20),
                extract_version=item.get("extract_version", 20),
                flag_bits=item.get("flag_bits", 0),
            )
            kind = item["kind"]
            if name == "Contents/header.xml":
                data = _xml_bytes(self.header_model)
            elif kind == "document-section" or _SECTION_RE.match(name):
                if section_cursor >= len(self.section_models):
                    continue
                data = _xml_bytes(self.section_models[section_cursor])
                section_cursor += 1
            elif kind == "xml":
                data = _xml_bytes(ElementModel.from_dict(item["model"]))
            elif kind == "asset":
                data = (self._base_dir / item["path"]).read_bytes()
            elif kind == "bytes":
                data = base64.b64decode(item["data_b64"])
            else:
                raise ValueError(f"unknown package item kind: {kind}")
            self._package.set(name, data, meta)
        source_names = set(order)
        for name in list(self._package.order):
            if name not in source_names:
                self._package.remove(name)
        self._package.reorder(order)

    def _sync_section_manifest(self) -> None:
        manifest = next((c for c in self.content_model.children if local_name(c.tag) == "manifest"), None)
        spine = next((c for c in self.content_model.children if local_name(c.tag) == "spine"), None)
        if manifest is None or spine is None:
            raise ValueError("content.hpf lacks manifest or spine")

        def is_section_item(node: ElementModel) -> bool:
            if local_name(node.tag) != "item":
                return False
            ident = node.get("id") or ""
            href = node.get("href") or ""
            return bool(re.fullmatch(r"section\d+", ident)) or bool(re.search(r"section\d+\.xml$", href))

        old_children = list(manifest.children)
        section_positions = [i for i, c in enumerate(old_children) if is_section_item(c)]
        rebuilt: list[ElementModel] = []
        cursor = 0
        last_insert_index: int | None = None
        for child in old_children:
            if is_section_item(child):
                if cursor < len(self.section_models):
                    child.set("id", f"section{cursor}")
                    child.set("href", f"Contents/section{cursor}.xml")
                    child.set("media-type", "application/xml")
                    rebuilt.append(child)
                    last_insert_index = len(rebuilt)
                    cursor += 1
                continue
            rebuilt.append(child)
        if cursor < len(self.section_models):
            if last_insert_index is None:
                last_insert_index = next(
                    (i + 1 for i, c in enumerate(rebuilt) if local_name(c.tag) == "item" and c.get("id") == "header"),
                    len(rebuilt),
                )
            extras = [
                ElementModel(OPF + "item", attrs=[
                    ("id", f"section{i}"), ("href", f"Contents/section{i}.xml"), ("media-type", "application/xml")
                ])
                for i in range(cursor, len(self.section_models))
            ]
            rebuilt[last_insert_index:last_insert_index] = extras
        manifest.children = rebuilt

        old_spine = list(spine.children)
        rebuilt_spine: list[ElementModel] = []
        cursor = 0
        last_spine_index: int | None = None
        for child in old_spine:
            is_section_ref = local_name(child.tag) == "itemref" and re.fullmatch(r"section\d+", child.get("idref") or "")
            if is_section_ref:
                if cursor < len(self.section_models):
                    child.set("idref", f"section{cursor}")
                    if child.get("linear") is None:
                        child.set("linear", "yes")
                    rebuilt_spine.append(child)
                    last_spine_index = len(rebuilt_spine)
                    cursor += 1
                continue
            rebuilt_spine.append(child)
        if cursor < len(self.section_models):
            if last_spine_index is None:
                last_spine_index = next(
                    (i + 1 for i, c in enumerate(rebuilt_spine) if local_name(c.tag) == "itemref" and c.get("idref") == "header"),
                    len(rebuilt_spine),
                )
            rebuilt_spine[last_spine_index:last_spine_index] = [
                ElementModel(OPF + "itemref", attrs=[("idref", f"section{i}"), ("linear", "yes")])
                for i in range(cursor, len(self.section_models))
            ]
        spine.children = rebuilt_spine
        self.header_model.set("secCnt", str(len(self.section_models)))

    def _sync_section_parts(self) -> None:
        old_order = list(self._package.order)
        existing = [name for name in old_order if _SECTION_RE.match(name)]
        new_names = [f"Contents/section{i}.xml" for i in range(len(self.section_models))]

        # Common edit path: section topology is unchanged. Preserve the exact
        # original bytes of every untouched section instead of serializing all
        # section parts just because one paragraph/table changed. Structural
        # add/remove/reorder falls through to the conservative rebuild below.
        baselines = getattr(self, "_baseline_section_models", [])
        if existing == new_names and len(baselines) == len(self.section_models):
            for i, model in enumerate(self.section_models):
                if self._model_differs(model, baselines[i]):
                    self._package.set(new_names[i], _xml_bytes(model), self._package.infos.get(new_names[i]))
            self._section_part_names = list(new_names)
            self._section_infos = [self._package.infos[name] for name in new_names]
            return
        first_info = (
            self._section_infos[0] if self._section_infos else
            self._package.infos.get(existing[0]) if existing else None
        )

        # Preserve each pre-existing section slot exactly when possible. Extra
        # sections are inserted immediately after the last section slot.
        desired: list[str] = []
        section_cursor = 0
        last_section_pos: int | None = None
        for name in old_order:
            if _SECTION_RE.match(name):
                if section_cursor < len(new_names):
                    desired.append(new_names[section_cursor])
                    last_section_pos = len(desired)
                    section_cursor += 1
                continue
            desired.append(name)
        if section_cursor < len(new_names):
            insert_at = last_section_pos if last_section_pos is not None else (desired.index("Contents/header.xml") + 1 if "Contents/header.xml" in desired else len(desired))
            desired[insert_at:insert_at] = new_names[section_cursor:]

        for name in existing:
            self._package.remove(name)
        for i, model in enumerate(self.section_models):
            name = new_names[i]
            meta = self._section_infos[i] if i < len(self._section_infos) else first_info
            if meta is not None:
                meta = PackageEntryInfo(
                    name=name, compress_type=meta.compress_type, date_time=meta.date_time,
                    comment=meta.comment, extra=meta.extra, internal_attr=meta.internal_attr,
                    external_attr=meta.external_attr, create_system=meta.create_system,
                    create_version=meta.create_version, extract_version=meta.extract_version,
                    flag_bits=meta.flag_bits,
                )
            self._package.set(name, _xml_bytes(model), meta)
        self._package.reorder(desired)
        self._section_part_names = new_names
        self._section_infos = [self._package.infos[name] for name in new_names]

    def _prepare_for_save(self) -> None:
        # Header/footer stories have a logical secPr copy and the hp:ctrl copy
        # Hancom consumes. Rich edits can happen through Paragraph/Run proxies,
        # so synchronize those twins as the final semantic step before writing.
        for section in self.sections:
            section.sync_story_mirrors()
        self.styles.prune_orphans()
        self._sync_section_manifest()
        if self._model_differs(self.header_model, getattr(self, "_baseline_header_model", None)):
            self._package.set("Contents/header.xml", _xml_bytes(self.header_model))
        if self._model_differs(self.content_model, getattr(self, "_baseline_content_model", None)):
            self._package.set("Contents/content.hpf", _xml_bytes(self.content_model))
        settings = getattr(self, "_settings_proxy", None)
        if settings is not None:
            settings._sync_to_package()
        self._sync_section_parts()

    def validate(self):
        """Return a validation report for the current in-memory document."""
        from .validation import validate_document_model
        self._prepare_for_save()
        return validate_document_model(self)

    def save(self, path: str | Path, *, validate: bool = True) -> None:
        """Save atomically, validating structural invariants by default.

        The target file is replaced only after the temporary HWPX passes ZIP,
        XML, shared-ID/reference, and public reopen checks. This is stricter
        than python-docx because one malformed shared ID can make Hancom reject
        an otherwise well-formed ZIP.
        """
        from .validation import validate_document_model, validate_hwpx_file
        self._prepare_for_save()
        if validate:
            validate_document_model(self).raise_for_errors()
        target = Path(path)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
        os.close(fd)
        tmp = Path(tmp_name)
        try:
            self._package.save(tmp)
            if validate:
                validate_hwpx_file(tmp).raise_for_errors()
            os.replace(tmp, target)
            self._capture_baselines()
            settings = getattr(self, "_settings_proxy", None)
            if settings is not None:
                settings._capture_baseline()
        finally:
            if tmp.exists():
                tmp.unlink()
