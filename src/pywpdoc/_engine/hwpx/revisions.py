"""HWPX tracked-revision writer used by the optional compare feature.

This module deliberately operates on the backend's lossless ElementModel so
existing HWPX package-preservation rules remain intact.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import PurePosixPath
from typing import Any

from ..core.errors import DocumentUnsupportedError
from ..authoring import paragraph_id
from ..model import ElementModel, HP, HH, Paragraph as NativeParagraph, local_name
from ..package import PackageEntryInfo


def _revision_date(value: str | None) -> str:
    if value:
        return str(value)
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clone(node: ElementModel) -> ElementModel:
    return ElementModel.from_dict(node.to_dict())


def _paragraphs(document: Any, everywhere: bool) -> list[Any]:
    return document._replace_paragraphs(everywhere=everywhere) if everywhere else list(document.paragraphs)


def _visible_runs(paragraph: Any, index: int) -> list[ElementModel]:
    result: list[ElementModel] = []
    for child in paragraph.element_model.children:
        name = local_name(child.tag)
        if name == "linesegarray":
            continue
        if name != "run":
            raise DocumentUnsupportedError(
                "tracked-text compare found unsupported inline structure in HWPX paragraph",
                code="compare-unsafe-inline-structure",
                context={"paragraph_index": index, "element": name, "format": "hwpx"},
            )
        text_nodes = [node for node in child.children if local_name(node.tag) == "t"]
        if not text_nodes:
            # Pure structural/control runs are preserved from the new document.
            continue
        if any(local_name(node.tag) != "t" for node in child.children):
            raise DocumentUnsupportedError(
                "changed HWPX paragraphs cannot mix text and controls in one run yet",
                code="compare-unsafe-inline-structure",
                context={"paragraph_index": index, "format": "hwpx"},
            )
        for text_node in text_nodes:
            if text_node.children:
                raise DocumentUnsupportedError(
                    "tracked-text compare supports plain HWPX text atoms only in changed paragraphs",
                    code="compare-unsafe-inline-structure",
                    context={"paragraph_index": index, "element": "t-mixed-content", "format": "hwpx"},
                )
        result.append(child)
    return result


def _run_records(paragraph: Any, index: int) -> list[tuple[int, int, ElementModel, str]]:
    records: list[tuple[int, int, ElementModel, str]] = []
    offset = 0
    for run in _visible_runs(paragraph, index):
        text = "".join((node.text or "") for node in run.children if local_name(node.tag) == "t")
        if not text:
            continue
        start = offset
        offset += len(text)
        records.append((start, offset, run, text))
    return records


def _plain_run_like(source: ElementModel, text: str) -> ElementModel:
    run = ElementModel(HP + "run", attrs=list(source.attrs))
    run.children.append(ElementModel(HP + "t", text=text))
    return run


def _tracked_run_like(
    source: ElementModel,
    text: str,
    *,
    kind: str,
    marker_id: int,
    change_id: int,
    paraend: bool = False,
) -> ElementModel:
    run = ElementModel(HP + "run", attrs=list(source.attrs))
    begin = ElementModel(
        HP + ("insertBegin" if kind == "insert" else "deleteBegin"),
        attrs=[("Id", str(marker_id)), ("TcId", str(change_id))],
    )
    end = ElementModel(
        HP + ("insertEnd" if kind == "insert" else "deleteEnd"),
        attrs=[("Id", str(marker_id)), ("TcId", str(change_id)), ("paraend", "1" if paraend else "0")],
    )
    begin.tail = text
    run.children.append(ElementModel(HP + "t", text="", children=[begin, end]))
    return run


def _slice_runs(
    paragraph: Any,
    index: int,
    start: int,
    end: int,
    *,
    kind: str | None = None,
    marker_counter: list[int] | None = None,
    change_id: int | None = None,
) -> list[ElementModel]:
    if start == end:
        return []
    out: list[ElementModel] = []
    for r_start, r_end, source, text in _run_records(paragraph, index):
        if r_end <= start or r_start >= end:
            continue
        local_start = max(start, r_start) - r_start
        local_end = min(end, r_end) - r_start
        piece = text[local_start:local_end]
        if not piece:
            continue
        if kind is None:
            out.append(_plain_run_like(source, piece))
        else:
            if marker_counter is None or change_id is None:
                raise RuntimeError("tracked HWPX slice requires marker/change ids")
            marker_id = marker_counter[0]
            marker_counter[0] += 1
            out.append(
                _tracked_run_like(
                    source, piece, kind=kind,
                    marker_id=marker_id, change_id=change_id,
                )
            )
    if not out:
        raise DocumentUnsupportedError(
            "tracked-text compare could not map text range back to HWPX runs",
            code="compare-text-map-failed",
            context={"paragraph_index": index, "start": start, "end": end, "format": "hwpx"},
        )
    return out


def _numeric_max(document: Any, tag_names: set[str], attr: str) -> int:
    maximum = 0
    for root in [document.header_model, *document.section_models]:
        for node in root.iter():
            if local_name(node.tag) not in tag_names:
                continue
            value = node.get(attr)
            try:
                maximum = max(maximum, int(value))
            except (TypeError, ValueError):
                continue
    return maximum


def _element_signature(node: ElementModel | None, *, ignore_id: bool = False):
    if node is None:
        return None
    attrs = tuple((k, v) for k, v in node.attrs if not (ignore_id and k == "id"))
    return (
        node.tag, attrs, node.text, node.tail,
        tuple(_element_signature(child, ignore_id=False) for child in node.children),
    )


def _property_container(document: Any, name: str) -> ElementModel | None:
    return next((node for node in document.header_model.iter() if local_name(node.tag) == name), None)


_FONT_REF_LANGS = {
    "hangul": "HANGUL",
    "latin": "LATIN",
    "hanja": "HANJA",
    "japanese": "JAPANESE",
    "other": "OTHER",
    "symbol": "SYMBOL",
    "user": "USER",
}


def _children_named(container: ElementModel | None, name: str) -> list[ElementModel]:
    if container is None:
        return []
    return [c for c in container.children if local_name(c.tag) == name]


def _next_numeric_id(container: ElementModel, child_name: str) -> str:
    maximum = -1
    for child in _children_named(container, child_name):
        try:
            maximum = max(maximum, int(child.get("id") or "-1"))
        except ValueError:
            continue
    return str(maximum + 1)


def _refresh_item_count(container: ElementModel, child_name: str, *, attr: str = "itemCnt") -> None:
    container.set(attr, str(len(_children_named(container, child_name))))


def _fontface_block(document: Any, lang: str) -> ElementModel | None:
    faces = _property_container(document, "fontfaces")
    if faces is None:
        return None
    return next(
        (c for c in faces.children if local_name(c.tag) == "fontface" and (c.get("lang") or "").upper() == lang),
        None,
    )


def _ensure_fontface_block(document: Any, lang: str) -> ElementModel:
    existing = _fontface_block(document, lang)
    if existing is not None:
        return existing
    faces = _property_container(document, "fontfaces")
    if faces is None:
        ref_list = next(
            (c for c in document.header_model.iter() if local_name(c.tag) == "refList"),
            None,
        )
        if ref_list is None:
            raise DocumentUnsupportedError(
                "new HWPX header has no refList for resource import",
                code="compare-hwpx-format-resource-container-missing",
                context={"resource": "fontfaces"},
            )
        faces = ElementModel(HH + "fontfaces", attrs=[("itemCnt", "0")])
        ref_list.children.insert(0, faces)
    block = ElementModel(HH + "fontface", attrs=[("lang", lang), ("fontCnt", "0")])
    faces.children.append(block)
    _refresh_item_count(faces, "fontface")
    return block


def _import_font(document: Any, old_document: Any, *, lang: str, old_font_id: str) -> str:
    old_block = _fontface_block(old_document, lang)
    old_font = None if old_block is None else next(
        (c for c in old_block.children if local_name(c.tag) == "font" and (c.get("id") or "0") == str(old_font_id)),
        None,
    )
    if old_font is None:
        raise DocumentUnsupportedError(
            "old HWPX character format references a missing font",
            code="compare-hwpx-format-source-resource-missing",
            context={"resource": "font", "lang": lang, "old_id": str(old_font_id)},
        )
    if (old_font.get("isEmbedded") or "0").strip().lower() in {"1", "true"}:
        raise DocumentUnsupportedError(
            "cross-document CharShape import does not copy embedded-font binary payloads",
            code="compare-hwpx-format-resource-dependency-unsupported",
            context={"resource": "embedded-font", "lang": lang, "old_id": str(old_font_id)},
        )
    target_block = _ensure_fontface_block(document, lang)
    wanted = _element_signature(old_font, ignore_id=True)
    for candidate in _children_named(target_block, "font"):
        if _element_signature(candidate, ignore_id=True) == wanted:
            return candidate.get("id") or "0"
    imported = _clone(old_font)
    imported.set("id", _next_numeric_id(target_block, "font"))
    target_block.children.append(imported)
    _refresh_item_count(target_block, "font", attr="fontCnt")
    return imported.get("id") or "0"


def _import_border_fill(document: Any, old_document: Any, old_border_id: str) -> str:
    old_container = _property_container(old_document, "borderFills")
    old_border = None if old_container is None else next(
        (c for c in old_container.children if local_name(c.tag) == "borderFill" and (c.get("id") or "0") == str(old_border_id)),
        None,
    )
    if old_border is None:
        raise DocumentUnsupportedError(
            "old HWPX formatting definition references a missing border fill",
            code="compare-hwpx-format-source-resource-missing",
            context={"resource": "borderFill", "old_id": str(old_border_id)},
        )
    for descendant in old_border.iter():
        for attr_name, attr_value in descendant.attrs:
            lname = local_name(attr_name).lower()
            if lname != "id" and (lname.endswith("idref") or lname.endswith("ref")):
                raise DocumentUnsupportedError(
                    "cross-document HWPX borderFill has an unverified external resource dependency",
                    code="compare-hwpx-format-resource-dependency-unsupported",
                    context={"resource": "borderFill", "attribute": local_name(attr_name), "value": attr_value},
                )
    target_container = _property_container(document, "borderFills")
    if target_container is None:
        raise DocumentUnsupportedError(
            "new HWPX header has no borderFills container for resource import",
            code="compare-hwpx-format-resource-container-missing",
            context={"resource": "borderFills"},
        )
    wanted = _element_signature(old_border, ignore_id=True)
    for candidate in _children_named(target_container, "borderFill"):
        if _element_signature(candidate, ignore_id=True) == wanted:
            return candidate.get("id") or "0"
    imported = _clone(old_border)
    imported.set("id", _next_numeric_id(target_container, "borderFill"))
    target_container.children.append(imported)
    _refresh_item_count(target_container, "borderFill")
    return imported.get("id") or "0"



_REF_COLLECTION_ORDER = [
    "fontfaces", "borderFills", "charProperties", "tabProperties",
    "numberings", "bullets", "paraProperties", "styles",
]
_NONE_CHAR_REF = {None, "", "4294967295", "-1"}


def _ensure_ref_collection_ordered(document: Any, name: str) -> ElementModel:
    existing = _property_container(document, name)
    if existing is not None:
        return existing
    ref_list = next((c for c in document.header_model.iter() if local_name(c.tag) == "refList"), None)
    if ref_list is None:
        raise DocumentUnsupportedError(
            "new HWPX header has no refList for resource import",
            code="compare-hwpx-format-resource-container-missing",
            context={"resource": name},
        )
    created = ElementModel(HH + name, attrs=[("itemCnt", "0")])
    wanted_index = _REF_COLLECTION_ORDER.index(name) if name in _REF_COLLECTION_ORDER else len(_REF_COLLECTION_ORDER)
    insert_at = len(ref_list.children)
    for index, child in enumerate(ref_list.children):
        lname = local_name(child.tag)
        child_index = _REF_COLLECTION_ORDER.index(lname) if lname in _REF_COLLECTION_ORDER else len(_REF_COLLECTION_ORDER)
        if child_index > wanted_index:
            insert_at = index
            break
    ref_list.children.insert(insert_at, created)
    return created


def _resource_by_id(document: Any, container_name: str, child_name: str, identifier: str | int | None) -> ElementModel | None:
    container = _property_container(document, container_name)
    if container is None:
        return None
    wanted = str(identifier if identifier is not None else "0")
    return next(
        (c for c in container.children if local_name(c.tag) == child_name and (c.get("id") or "0") == wanted),
        None,
    )


def _assert_no_unverified_refs(node: ElementModel, *, resource: str, allowed: set[str] | None = None) -> None:
    permitted = set(allowed or ())
    for descendant in node.iter():
        for attr_name, attr_value in descendant.attrs:
            lname = local_name(attr_name)
            lower = lname.lower()
            if lname in permitted or lname == "id":
                continue
            if lower.endswith("idref") or lower.endswith("ref"):
                raise DocumentUnsupportedError(
                    f"cross-document {resource} has an unverified external resource dependency",
                    code="compare-hwpx-format-resource-dependency-unsupported",
                    context={"resource": resource, "attribute": lname, "value": attr_value},
                )


def _resolved_tab_signature(document: Any, tab_id: str | int | None):
    tab = _resource_by_id(document, "tabProperties", "tabPr", tab_id)
    if tab is None:
        return ("missing-tabPr", str(tab_id))
    return _element_signature(tab, ignore_id=True)


def _import_tab_pr(document: Any, old_document: Any, old_tab_id: str | int | None) -> str:
    old_tab = _resource_by_id(old_document, "tabProperties", "tabPr", old_tab_id)
    if old_tab is None:
        raise DocumentUnsupportedError(
            "old HWPX paragraph format references a missing tab definition",
            code="compare-hwpx-format-source-resource-missing",
            context={"resource": "tabPr", "old_id": str(old_tab_id)},
        )
    _assert_no_unverified_refs(old_tab, resource="tabPr")
    target = _property_container(document, "tabProperties")
    if target is None:
        raise DocumentUnsupportedError(
            "new HWPX header has no tabProperties container for resource import",
            code="compare-hwpx-format-resource-container-missing",
            context={"resource": "tabProperties"},
        )
    wanted = _element_signature(old_tab, ignore_id=True)
    for candidate in _children_named(target, "tabPr"):
        if _element_signature(candidate, ignore_id=True) == wanted:
            return candidate.get("id") or "0"
    imported = _clone(old_tab)
    imported.set("id", _next_numeric_id(target, "tabPr"))
    target.children.append(imported)
    _refresh_item_count(target, "tabPr")
    return imported.get("id") or "0"


def _resolved_para_head_signature(document: Any, head: ElementModel):
    attrs = tuple((k, v) for k, v in head.attrs if k != "charPrIDRef")
    char_ref = head.get("charPrIDRef")
    if char_ref in _NONE_CHAR_REF:
        char_sig = char_ref
    else:
        char_node = document.styles.char_property(char_ref)
        char_sig = ("missing-charPr", str(char_ref)) if char_node is None else _resolved_char_property_signature(document, char_node)
    return (
        head.tag, attrs, char_sig, head.text, head.tail,
        tuple(_element_signature(child, ignore_id=False) for child in head.children),
    )


def _resolved_numbering_signature(document: Any, numbering: ElementModel):
    attrs = tuple((k, v) for k, v in numbering.attrs if k != "id")
    children = []
    for child in numbering.children:
        if local_name(child.tag) == "paraHead":
            children.append(_resolved_para_head_signature(document, child))
        else:
            children.append(_element_signature(child, ignore_id=False))
    return (numbering.tag, attrs, numbering.text, numbering.tail, tuple(children))


def _remap_para_head_char_refs(document: Any, old_document: Any, source: ElementModel, clone: ElementModel) -> None:
    old_heads = [c for c in source.children if local_name(c.tag) == "paraHead"]
    new_heads = [c for c in clone.children if local_name(c.tag) == "paraHead"]
    if len(old_heads) != len(new_heads):  # pragma: no cover - clone preserves topology
        raise DocumentUnsupportedError(
            "HWPX paragraph resource clone changed paraHead topology",
            code="compare-hwpx-format-resource-remap-failed",
        )
    for old_head, new_head in zip(old_heads, new_heads):
        char_ref = old_head.get("charPrIDRef")
        if char_ref in _NONE_CHAR_REF:
            continue
        new_head.set(
            "charPrIDRef",
            _matching_old_property_id(document, old_document, kind="char", old_id=char_ref),
        )


def _import_numbering(document: Any, old_document: Any, old_numbering_id: str | int | None) -> str:
    old_numbering = _resource_by_id(old_document, "numberings", "numbering", old_numbering_id)
    if old_numbering is None:
        raise DocumentUnsupportedError(
            "old HWPX paragraph format references a missing numbering definition",
            code="compare-hwpx-format-source-resource-missing",
            context={"resource": "numbering", "old_id": str(old_numbering_id)},
        )
    _assert_no_unverified_refs(old_numbering, resource="numbering", allowed={"charPrIDRef"})
    target = _ensure_ref_collection_ordered(document, "numberings")
    wanted = _resolved_numbering_signature(old_document, old_numbering)
    for candidate in _children_named(target, "numbering"):
        if _resolved_numbering_signature(document, candidate) == wanted:
            return candidate.get("id") or "1"
    imported = _clone(old_numbering)
    imported.attrs[:] = [(k, v) for k, v in imported.attrs if k != "id"]
    _remap_para_head_char_refs(document, old_document, old_numbering, imported)
    next_id = max(1, int(_next_numeric_id(target, "numbering")))
    imported.set("id", str(next_id))
    target.children.append(imported)
    _refresh_item_count(target, "numbering")
    return imported.get("id") or "1"


def _resolved_bullet_signature(document: Any, bullet: ElementModel):
    attrs = tuple((k, v) for k, v in bullet.attrs if k != "id")
    children = []
    for child in bullet.children:
        if local_name(child.tag) == "paraHead":
            children.append(_resolved_para_head_signature(document, child))
        elif local_name(child.tag) == "img":
            img_attrs = tuple((k, v) for k, v in child.attrs if local_name(k) != "binaryItemIDRef")
            binary_ref = child.get("binaryItemIDRef")
            children.append((
                child.tag,
                img_attrs,
                _resolved_binary_item_signature(document, binary_ref),
                child.text,
                child.tail,
                tuple(_element_signature(grandchild, ignore_id=False) for grandchild in child.children),
            ))
        else:
            children.append(_element_signature(child, ignore_id=False))
    return (bullet.tag, attrs, bullet.text, bullet.tail, tuple(children))


def _manifest(document: Any) -> ElementModel | None:
    return next((node for node in document.content_model.iter() if local_name(node.tag) == "manifest"), None)


def _manifest_item(document: Any, item_id: str | int | None) -> ElementModel | None:
    manifest = _manifest(document)
    if manifest is None:
        return None
    wanted = str(item_id if item_id is not None else "")
    return next(
        (child for child in manifest.children if local_name(child.tag) == "item" and (child.get("id") or "") == wanted),
        None,
    )


def _resolved_binary_item_signature(document: Any, item_id: str | int | None):
    item = _manifest_item(document, item_id)
    if item is None:
        return ("missing-manifest-item", str(item_id))
    href = item.get("href") or ""
    payload = document._package.parts.get(href)
    if payload is None:
        return ("missing-binary-payload", tuple((k, v) for k, v in item.attrs if k not in {"id", "href"}), href)
    attrs = tuple((k, v) for k, v in item.attrs if k not in {"id", "href"})
    return ("binary-item", attrs, sha256(payload).hexdigest(), len(payload))


def _copy_package_entry_info(source: Any, *, name: str, fallback_document: Any) -> PackageEntryInfo:
    info = source
    if info is None:
        info = fallback_document._package.infos.get("Contents/section0.xml")
    if info is None:  # pragma: no cover - every supported package has section0
        return PackageEntryInfo(name, 8, (2026, 1, 1, 0, 0, 0))
    return PackageEntryInfo(
        name=name,
        compress_type=info.compress_type,
        date_time=info.date_time,
        comment=info.comment,
        extra=info.extra,
        internal_attr=info.internal_attr,
        external_attr=info.external_attr,
        create_system=info.create_system,
        create_version=info.create_version,
        extract_version=info.extract_version,
        flag_bits=info.flag_bits,
    )


def _import_binary_item(document: Any, old_document: Any, old_item_id: str | int | None) -> str:
    old_item = _manifest_item(old_document, old_item_id)
    if old_item is None:
        raise DocumentUnsupportedError(
            "old HWPX image bullet references a missing manifest item",
            code="compare-hwpx-format-source-resource-missing",
            context={"resource": "image-bullet-binary", "old_id": str(old_item_id)},
        )
    old_href = old_item.get("href") or ""
    old_payload = old_document._package.parts.get(old_href)
    if not old_href or old_payload is None:
        raise DocumentUnsupportedError(
            "old HWPX image bullet references a missing binary payload",
            code="compare-hwpx-format-source-resource-missing",
            context={"resource": "image-bullet-binary", "old_id": str(old_item_id), "href": old_href},
        )
    if (old_item.get("isEmbeded") or "1").strip().lower() not in {"1", "true"}:
        raise DocumentUnsupportedError(
            "cross-document image-bullet import does not copy external binary references",
            code="compare-hwpx-format-resource-dependency-unsupported",
            context={"resource": "image-bullet-binary", "old_id": str(old_item_id)},
        )
    old_media_type = old_item.get("media-type") or ""
    if old_media_type and not old_media_type.lower().startswith("image/"):
        raise DocumentUnsupportedError(
            "image bullet manifest item is not an image media type",
            code="compare-hwpx-format-resource-dependency-unsupported",
            context={"resource": "image-bullet-binary", "media_type": old_media_type},
        )

    manifest = _manifest(document)
    if manifest is None:
        raise DocumentUnsupportedError(
            "new HWPX package has no content manifest for image-bullet import",
            code="compare-hwpx-format-resource-container-missing",
            context={"resource": "content-manifest"},
        )
    wanted = _resolved_binary_item_signature(old_document, old_item_id)
    for candidate in manifest.children:
        if local_name(candidate.tag) != "item":
            continue
        candidate_id = candidate.get("id")
        if candidate_id and _resolved_binary_item_signature(document, candidate_id) == wanted:
            return candidate_id

    suffix = PurePosixPath(old_href).suffix.lower()
    if not suffix:
        suffix = {
            "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/bmp": ".bmp",
        }.get(old_media_type.lower(), "")
    if not suffix:
        raise DocumentUnsupportedError(
            "image bullet binary format cannot be mapped into the target package",
            code="compare-hwpx-format-resource-dependency-unsupported",
            context={"resource": "image-bullet-binary", "href": old_href, "media_type": old_media_type},
        )

    used_ids = {child.get("id") for child in manifest.children if local_name(child.tag) == "item"}
    index = 1
    while True:
        item_id = f"image{index}"
        href = f"BinData/{item_id}{suffix}"
        if item_id not in used_ids and href not in document._package.parts:
            break
        index += 1

    imported = _clone(old_item)
    imported.set("id", item_id)
    imported.set("href", href)
    manifest.children.append(imported)
    old_info = old_document._package.infos.get(old_href)
    document._package.set(
        href,
        bytes(old_payload),
        _copy_package_entry_info(old_info, name=href, fallback_document=document),
    )
    return item_id


def _import_bullet(document: Any, old_document: Any, old_bullet_id: str | int | None) -> str:
    old_bullet = _resource_by_id(old_document, "bullets", "bullet", old_bullet_id)
    if old_bullet is None:
        raise DocumentUnsupportedError(
            "old HWPX paragraph format references a missing bullet definition",
            code="compare-hwpx-format-source-resource-missing",
            context={"resource": "bullet", "old_id": str(old_bullet_id)},
        )
    is_image_bullet = (old_bullet.get("useImage") or "0").strip().lower() in {"1", "true"} or any(
        local_name(c.tag) == "img" for c in old_bullet.children
    )
    _assert_no_unverified_refs(
        old_bullet,
        resource="bullet",
        allowed={"charPrIDRef", "binaryItemIDRef"} if is_image_bullet else {"charPrIDRef"},
    )
    target = _ensure_ref_collection_ordered(document, "bullets")
    wanted = _resolved_bullet_signature(old_document, old_bullet)
    for candidate in _children_named(target, "bullet"):
        if _resolved_bullet_signature(document, candidate) == wanted:
            return candidate.get("id") or "1"
    imported = _clone(old_bullet)
    imported.attrs[:] = [(k, v) for k, v in imported.attrs if k != "id"]
    _remap_para_head_char_refs(document, old_document, old_bullet, imported)
    if is_image_bullet:
        old_images = [c for c in old_bullet.children if local_name(c.tag) == "img"]
        new_images = [c for c in imported.children if local_name(c.tag) == "img"]
        if not old_images or len(old_images) != len(new_images):
            raise DocumentUnsupportedError(
                "HWPX image bullet has no stable image-reference topology",
                code="compare-hwpx-format-resource-remap-failed",
                context={"resource": "image-bullet", "old_id": str(old_bullet_id)},
            )
        for old_img, new_img in zip(old_images, new_images):
            binary_ref = old_img.get("binaryItemIDRef")
            if not binary_ref:
                raise DocumentUnsupportedError(
                    "HWPX image bullet image node has no binaryItemIDRef",
                    code="compare-hwpx-format-source-resource-missing",
                    context={"resource": "image-bullet-binary", "old_id": str(old_bullet_id)},
                )
            new_img.set("binaryItemIDRef", _import_binary_item(document, old_document, binary_ref))
    next_id = max(1, int(_next_numeric_id(target, "bullet")))
    imported.set("id", str(next_id))
    target.children.append(imported)
    _refresh_item_count(target, "bullet")
    return imported.get("id") or "1"


def _resolved_para_property_signature(document: Any, node: ElementModel):
    attrs = tuple((k, v) for k, v in node.attrs if k not in {"id", "tabPrIDRef"})
    tab_sig = _resolved_tab_signature(document, node.get("tabPrIDRef") or "0")
    children = []
    for child in node.children:
        lname = local_name(child.tag)
        if lname == "border":
            border_attrs = tuple((k, v) for k, v in child.attrs if k != "borderFillIDRef")
            border_ref = child.get("borderFillIDRef")
            border_node = _resource_by_id(document, "borderFills", "borderFill", border_ref) if border_ref is not None else None
            border_sig = None if border_ref is None else (("missing-borderFill", str(border_ref)) if border_node is None else _element_signature(border_node, ignore_id=True))
            children.append((child.tag, border_attrs, border_sig, child.text, child.tail, tuple(_element_signature(c) for c in child.children)))
            continue
        if lname == "heading":
            heading_attrs = tuple((k, v) for k, v in child.attrs if k != "idRef")
            htype = (child.get("type") or "NONE").upper()
            href = child.get("idRef") or "0"
            if htype in {"NONE", "OUTLINE"} and href == "0":
                resource_sig = ("builtin", htype, href)
            elif htype in {"NUMBER", "OUTLINE"}:
                resource = _resource_by_id(document, "numberings", "numbering", href)
                resource_sig = ("missing-numbering", href) if resource is None else _resolved_numbering_signature(document, resource)
            elif htype == "BULLET":
                resource = _resource_by_id(document, "bullets", "bullet", href)
                resource_sig = ("missing-bullet", href) if resource is None else _resolved_bullet_signature(document, resource)
            else:
                resource_sig = ("unsupported-heading", htype, href)
            children.append((child.tag, heading_attrs, resource_sig, child.text, child.tail, tuple(_element_signature(c) for c in child.children)))
            continue
        children.append(_element_signature(child, ignore_id=False))
    return (node.tag, attrs, tab_sig, node.text, node.tail, tuple(children))


def _remapped_old_para_property(document: Any, old_document: Any, old_node: ElementModel) -> ElementModel:
    imported = _clone(old_node)
    imported.attrs[:] = [(k, v) for k, v in imported.attrs if k != "id"]

    imported.set("tabPrIDRef", _import_tab_pr(document, old_document, old_node.get("tabPrIDRef") or "0"))

    old_border = next((c for c in old_node.children if local_name(c.tag) == "border"), None)
    new_border = next((c for c in imported.children if local_name(c.tag) == "border"), None)
    if old_border is not None and new_border is not None and old_border.get("borderFillIDRef") is not None:
        new_border.set("borderFillIDRef", _import_border_fill(document, old_document, old_border.get("borderFillIDRef") or "0"))

    old_heading = next((c for c in old_node.children if local_name(c.tag) == "heading"), None)
    new_heading = next((c for c in imported.children if local_name(c.tag) == "heading"), None)
    if old_heading is not None and new_heading is not None:
        htype = (old_heading.get("type") or "NONE").upper()
        href = old_heading.get("idRef") or "0"
        if htype in {"NONE", "OUTLINE"} and href == "0":
            pass
        elif htype in {"NUMBER", "OUTLINE"}:
            new_heading.set("idRef", _import_numbering(document, old_document, href))
        elif htype == "BULLET":
            new_heading.set("idRef", _import_bullet(document, old_document, href))
        else:
            raise DocumentUnsupportedError(
                "cross-document ParaShape import found an unsupported heading type",
                code="compare-hwpx-format-resource-dependency-unsupported",
                context={"resource": "heading", "type": htype, "idRef": href},
            )
    return imported


def _style_shallow_identity_signature(style_node: ElementModel):
    """Return the non-format identity of one HWPX named style.

    HWPX style ids and property ids are header-local.  Track Changes can
    restore CharShape/ParaShape values, but the verified model has no separate
    revision record for changing a paragraph's named-style identity.  Treat
    name/type/language/lock metadata (plus unknown non-reference attributes) as
    identity, while paraPr/charPr/next-style ids are resolved separately.
    """
    attrs = tuple(
        (k, v) for k, v in style_node.attrs
        if k not in {"id", "paraPrIDRef", "charPrIDRef", "nextStyleIDRef"}
    )
    return (
        style_node.tag, attrs, style_node.text, style_node.tail,
        tuple(_element_signature(child, ignore_id=False) for child in style_node.children),
    )


def _resolved_style_identity_signature(document: Any, style_id: str | int | None):
    """Resolve header-local style ids to a conservative semantic identity.

    This intentionally excludes char/paragraph property references: those are
    tracked independently as CharShape/ParaShape revisions.  ``nextStyleIDRef``
    is part of style behavior, so compare its target's shallow identity rather
    than its local numeric id.
    """
    style = document.styles.get(style_id)
    if style is None:
        return ("missing-style", str(style_id if style_id is not None else "0"))
    node = style.element_model
    next_ref = node.get("nextStyleIDRef")
    if next_ref is None:
        next_sig = None
    else:
        target = document.styles.get(next_ref)
        next_sig = (
            ("missing-next-style", str(next_ref))
            if target is None else _style_shallow_identity_signature(target.element_model)
        )
    return (_style_shallow_identity_signature(node), next_sig)


def _resolved_char_property_signature(document: Any, node: ElementModel):
    attrs = tuple(
        (k, v) for k, v in node.attrs
        if k not in {"id", "borderFillIDRef"}
    )
    border_sig = None
    border_id = node.get("borderFillIDRef")
    if border_id is not None:
        border_container = _property_container(document, "borderFills")
        border = None if border_container is None else next(
            (c for c in border_container.children if local_name(c.tag) == "borderFill" and (c.get("id") or "0") == str(border_id)),
            None,
        )
        if border is None:
            return ("missing-border", str(border_id), attrs)
        border_sig = _element_signature(border, ignore_id=True)

    child_sigs = []
    for child in node.children:
        if local_name(child.tag) != "fontRef":
            child_sigs.append(_element_signature(child, ignore_id=False))
            continue
        refs = []
        for attr, lang in _FONT_REF_LANGS.items():
            font_id = child.get(attr)
            if font_id is None:
                refs.append((attr, None))
                continue
            block = _fontface_block(document, lang)
            font = None if block is None else next(
                (c for c in block.children if local_name(c.tag) == "font" and (c.get("id") or "0") == str(font_id)),
                None,
            )
            if font is None:
                refs.append((attr, ("missing-font", str(font_id))))
            else:
                refs.append((attr, _element_signature(font, ignore_id=True)))
        child_sigs.append((child.tag, tuple(refs), child.text, child.tail))
    return (node.tag, attrs, border_sig, tuple(child_sigs))


def _remapped_old_char_property(document: Any, old_document: Any, old_node: ElementModel) -> ElementModel:
    imported = _clone(old_node)
    imported.attrs[:] = [(k, v) for k, v in imported.attrs if k != "id"]

    font_ref = next((c for c in imported.children if local_name(c.tag) == "fontRef"), None)
    old_font_ref = next((c for c in old_node.children if local_name(c.tag) == "fontRef"), None)
    if old_font_ref is not None:
        if font_ref is None:  # pragma: no cover - clone preserves children
            raise DocumentUnsupportedError(
                "old HWPX character format fontRef could not be cloned",
                code="compare-hwpx-format-resource-remap-failed",
            )
        for attr, lang in _FONT_REF_LANGS.items():
            old_font_id = old_font_ref.get(attr)
            if old_font_id is not None:
                font_ref.set(attr, _import_font(document, old_document, lang=lang, old_font_id=old_font_id))

    old_border_id = old_node.get("borderFillIDRef")
    if old_border_id is not None:
        imported.set("borderFillIDRef", _import_border_fill(document, old_document, old_border_id))
    return imported


def _matching_old_property_id(
    document: Any, old_document: Any, *, kind: str, old_id: str | int | None,
) -> str:
    if kind == "char":
        old_node = old_document.styles.char_property(old_id)
        container_name, child_name = "charProperties", "charPr"
    elif kind == "para":
        old_node = old_document.styles.paragraph_property(old_id)
        container_name, child_name = "paraProperties", "paraPr"
    else:  # pragma: no cover - defensive
        raise ValueError(kind)
    if old_node is None:
        raise DocumentUnsupportedError(
            "old HWPX formatting definition is missing",
            code="compare-hwpx-format-source-style-missing",
            context={"kind": kind, "old_id": str(old_id)},
        )

    container = _property_container(document, container_name)
    if container is None:
        raise DocumentUnsupportedError(
            "new HWPX formatting property container is missing",
            code="compare-hwpx-format-resource-container-missing",
            context={"resource": container_name},
        )

    # Same-header/template fast path.  CharShape equality must resolve resource
    # references: identical numeric font ids in unrelated headers may point to
    # completely different typefaces.
    if kind == "char":
        wanted = _resolved_char_property_signature(old_document, old_node)
        for candidate in container.children:
            if local_name(candidate.tag) == child_name and _resolved_char_property_signature(document, candidate) == wanted:
                return candidate.get("id") or "0"
        # v0.35.0: import the OLD CharShape dependency graph into the review clone.
        remapped = _remapped_old_char_property(document, old_document, old_node)
        remapped_sig = _resolved_char_property_signature(document, remapped)
        for candidate in container.children:
            if local_name(candidate.tag) == "charPr" and _resolved_char_property_signature(document, candidate) == remapped_sig:
                return candidate.get("id") or "0"
        remapped.set("id", _next_numeric_id(container, "charPr"))
        container.children.append(remapped)
        _refresh_item_count(container, "charPr")
        return remapped.get("id") or "0"

    wanted = _resolved_para_property_signature(old_document, old_node)
    for candidate in container.children:
        if local_name(candidate.tag) == child_name and _resolved_para_property_signature(document, candidate) == wanted:
            return candidate.get("id") or "0"

    # v0.37.0: import/remap the OLD ParaShape dependency graph.  This covers
    # tabPr, paragraph borderFill, numbering/bullet definitions, and any
    # paraHead charPr dependencies. The source NEW document remains untouched.
    remapped = _remapped_old_para_property(document, old_document, old_node)
    remapped_sig = _resolved_para_property_signature(document, remapped)
    for candidate in container.children:
        if local_name(candidate.tag) == "paraPr" and _resolved_para_property_signature(document, candidate) == remapped_sig:
            return candidate.get("id") or "0"
    remapped.set("id", _next_numeric_id(container, "paraPr"))
    container.children.append(remapped)
    _refresh_item_count(container, "paraPr")
    return remapped.get("id") or "0"


def _run_for_range(paragraph: Any, index: int, start: int, end: int) -> ElementModel:
    for r_start, r_end, run, _text in _run_records(paragraph, index):
        if r_start <= start and end <= r_end and start < end:
            return run
    raise DocumentUnsupportedError(
        "HWPX format-change range does not map to one source run",
        code="compare-format-map-failed",
        context={"paragraph_index": index, "start": start, "end": end, "format": "hwpx"},
    )


def _assert_no_existing_format_revision(paragraph: Any, index: int) -> None:
    if paragraph.element_model.get("paraTcId") not in (None, "", "0"):
        raise DocumentUnsupportedError(
            "HWPX paragraph already has a formatting revision",
            code="compare-existing-revisions-unsupported",
            context={"paragraph_index": index, "format": "hwpx", "kind": "ParaShape"},
        )
    for run in paragraph.element_model.children:
        if local_name(run.tag) != "run":
            continue
        # Hancom 2020 native CharShape tracking uses paraTcId on the run,
        # despite the public paragraph schema also exposing charTcId. Accept
        # either spelling as an existing revision marker and never overlap it.
        if run.get("paraTcId") not in (None, "", "0") or run.get("charTcId") not in (None, "", "0"):
            raise DocumentUnsupportedError(
                "HWPX run already has a formatting revision",
                code="compare-existing-revisions-unsupported",
                context={"paragraph_index": index, "format": "hwpx", "kind": "CharShape"},
            )


def _mark_char_format_range(
    paragraph: Any, index: int, start: int, end: int, *, change_id: int,
) -> None:
    if start >= end:
        return
    # Formatting tracking is intentionally limited to plain text runs. This is
    # the same safety boundary as changed-text rewriting, but no text is altered.
    _visible_runs(paragraph, index)
    rebuilt: list[ElementModel] = []
    offset = 0
    touched = False
    for child in paragraph.element_model.children:
        name = local_name(child.tag)
        if name == "linesegarray":
            continue
        if name != "run":
            rebuilt.append(child)
            continue
        text = "".join((node.text or "") for node in child.children if local_name(node.tag) == "t")
        if not text:
            rebuilt.append(child)
            continue
        r_start, r_end = offset, offset + len(text)
        offset = r_end
        overlap_start, overlap_end = max(start, r_start), min(end, r_end)
        if overlap_start >= overlap_end:
            rebuilt.append(child)
            continue
        before = text[: overlap_start - r_start]
        middle = text[overlap_start - r_start : overlap_end - r_start]
        after = text[overlap_end - r_start :]
        if before:
            rebuilt.append(_plain_run_like(child, before))
        tracked = _plain_run_like(child, middle)
        tracked.set("paraTcId", str(change_id))
        rebuilt.append(tracked)
        if after:
            rebuilt.append(_plain_run_like(child, after))
        touched = True
    if not touched:
        raise DocumentUnsupportedError(
            "HWPX format-change range could not be applied to output runs",
            code="compare-format-map-failed",
            context={"paragraph_index": index, "start": start, "end": end, "format": "hwpx"},
        )
    paragraph.element_model.children[:] = rebuilt
    paragraph._clear_layout_cache()


class _HeaderRevisionRegistry:
    def __init__(self, document: Any, author: str, date: str | None):
        self.document = document
        self.author = author
        self.date = _revision_date(date)
        self.ref_list = next(
            (c for c in document.header_model.children if local_name(c.tag) == "refList"),
            None,
        )
        if self.ref_list is None:
            self.ref_list = ElementModel(HH + "refList")
            document.header_model.children.insert(1, self.ref_list)
        self.authors = next(
            (c for c in self.ref_list.children if local_name(c.tag) == "trackChangeAuthors"),
            None,
        )
        if self.authors is None:
            self.authors = ElementModel(HH + "trackChangeAuthors", attrs=[("itemCnt", "0")])
            self.ref_list.children.append(self.authors)
        self.changes = next(
            (c for c in self.ref_list.children if local_name(c.tag) == "trackChanges"),
            None,
        )
        if self.changes is None:
            self.changes = ElementModel(HH + "trackChanges", attrs=[("itemCnt", "0")])
            # Hancom convention keeps change records before author records.
            author_index = self.ref_list.children.index(self.authors)
            self.ref_list.children.insert(author_index, self.changes)
        self.author_id = self._ensure_author()
        self.next_change_id = _numeric_max(document, {"trackChange"}, "id") + 1
        self._enable_config()

    def _ensure_author(self) -> int:
        for node in self.authors.children:
            if local_name(node.tag) == "trackChangeAuthor" and (node.get("name") or "") == self.author:
                try:
                    return int(node.get("id") or "0")
                except ValueError:
                    break
        next_id = _numeric_max(self.document, {"trackChangeAuthor"}, "id") + 1
        self.authors.children.append(
            ElementModel(
                HH + "trackChangeAuthor",
                attrs=[("id", str(next_id)), ("name", self.author), ("mark", "1")],
            )
        )
        self.authors.set("itemCnt", str(len([
            c for c in self.authors.children if local_name(c.tag) == "trackChangeAuthor"
        ])))
        return next_id

    def _enable_config(self) -> None:
        config = next(
            (
                c for c in self.document.header_model.children
                if local_name(c.tag).lower() in {"trackchageconfig", "trackchangeconfig"}
            ),
            None,
        )
        if config is None:
            config = ElementModel(HH + "trackchageConfig", attrs=[("flags", "1")])
            self.document.header_model.children.append(config)
            return
        try:
            flags = int(config.get("flags", "0") or 0)
        except ValueError:
            flags = 0
        config.set("flags", str(flags | 1))

    def add(self, kind: str) -> int:
        change_id = self.next_change_id
        self.next_change_id += 1
        self.changes.children.append(
            ElementModel(
                HH + "trackChange",
                attrs=[
                    ("id", str(change_id)),
                    ("type", "Insert" if kind == "insert" else "Delete"),
                    ("date", self.date),
                    ("authorID", str(self.author_id)),
                    ("hide", "0"),
                ],
            )
        )
        self._refresh_count()
        return change_id

    def add_format(self, kind: str, old_shape_id: str | int) -> int:
        if kind not in {"CharShape", "ParaShape"}:
            raise ValueError(kind)
        change_id = self.next_change_id
        self.next_change_id += 1
        # Hancom 2020 native output uses lower-case "shape" here
        # (charshapeID/parashapeID), even though some published schemas show
        # charShapeID/paraShapeID. Native-editor output is the compatibility
        # oracle for authored review files.
        shape_attr = "charshapeID" if kind == "CharShape" else "parashapeID"
        self.changes.children.append(
            ElementModel(
                HH + "trackChange",
                attrs=[
                    ("id", str(change_id)),
                    ("type", kind),
                    ("date", self.date),
                    ("authorID", str(self.author_id)),
                    ("hide", "0"),
                    (shape_attr, str(old_shape_id)),
                ],
            )
        )
        self._refresh_count()
        return change_id

    def _refresh_count(self) -> None:
        self.changes.set("itemCnt", str(len([
            c for c in self.changes.children if local_name(c.tag) == "trackChange"
        ])))


def _body_blocks(document: Any) -> list[Any]:
    return list(document.iter_inner_content())


def _is_paragraph_block(block: Any) -> bool:
    return "paragraph" in type(block).__name__.lower()


def _assert_structural_paragraph_safe(paragraph: Any, block_index: int) -> list[ElementModel]:
    runs: list[ElementModel] = []
    for child in paragraph.element_model.children:
        name = local_name(child.tag)
        if name == "linesegarray":
            continue
        if name != "run":
            raise DocumentUnsupportedError(
                "HWPX paragraph structural revision contains unsupported structure",
                code="compare-paragraph-copy-unsafe",
                context={"block_index": block_index, "element": name, "format": "hwpx"},
            )
        if any(local_name(node.tag) != "t" for node in child.children):
            raise DocumentUnsupportedError(
                "HWPX paragraph structural revision supports plain text runs only",
                code="compare-paragraph-copy-unsafe",
                context={"block_index": block_index, "format": "hwpx"},
            )
        for text_node in child.children:
            if text_node.children:
                raise DocumentUnsupportedError(
                    "HWPX paragraph already contains inline markup/revisions",
                    code="compare-existing-revisions-unsupported",
                    context={"block_index": block_index, "format": "hwpx"},
                )
        runs.append(child)
    return runs


def _mark_whole_paragraph(
    paragraph: Any,
    *,
    kind: str,
    registry: _HeaderRevisionRegistry,
    marker_counter: list[int],
    block_index: int,
) -> None:
    source_runs = _assert_structural_paragraph_safe(paragraph, block_index)
    change_id = registry.add(kind)
    pieces: list[tuple[ElementModel, str]] = []
    for run in source_runs:
        text = "".join((node.text or "") for node in run.children if local_name(node.tag) == "t")
        if text:
            pieces.append((run, text))

    rebuilt: list[ElementModel] = []
    if pieces:
        for i, (source, text) in enumerate(pieces):
            marker_id = marker_counter[0]
            marker_counter[0] += 1
            rebuilt.append(_tracked_run_like(
                source, text, kind=kind, marker_id=marker_id, change_id=change_id,
                paraend=i == len(pieces) - 1,
            ))
    else:
        source = source_runs[0] if source_runs else ElementModel(
            HP + "run", attrs=[("charPrIDRef", "0")]
        )
        marker_id = marker_counter[0]
        marker_counter[0] += 1
        rebuilt.append(_tracked_run_like(
            source, "", kind=kind, marker_id=marker_id, change_id=change_id, paraend=True,
        ))

    paragraph.element_model.children[:] = rebuilt
    paragraph._clear_layout_cache()


def _top_level_paragraph_for_block(document: Any, block: Any) -> tuple[ElementModel, ElementModel]:
    target = block.element_model
    for section in document.section_models:
        for child in section.children:
            if local_name(child.tag) != "p":
                continue
            if child is target or any(node is target for node in child.iter()):
                return section, child
    raise DocumentUnsupportedError(
        "body block anchor is not attached to a top-level HWPX paragraph",
        code="compare-paragraph-alignment-ambiguous",
    )


def _insert_body_paragraph(document: Any, index: int, paragraph_model: ElementModel) -> None:
    blocks = _body_blocks(document)
    if not 0 <= index <= len(blocks):
        raise DocumentUnsupportedError(
            "paragraph insertion anchor moved while applying revisions",
            code="compare-paragraph-alignment-ambiguous",
            context={"block_index": index, "block_count": len(blocks), "format": "hwpx"},
        )
    if index < len(blocks):
        section, anchor = _top_level_paragraph_for_block(document, blocks[index])
        anchor_index = next(i for i, child in enumerate(section.children) if child is anchor)
        section.children.insert(anchor_index, paragraph_model)
        return
    if not document.section_models:
        raise DocumentUnsupportedError(
            "HWPX document has no section for paragraph insertion",
            code="compare-paragraph-alignment-ambiguous",
        )
    document.section_models[-1].children.append(paragraph_model)


def _apply_body_paragraph_revisions(
    document: Any,
    old_document: Any,
    revisions: Any,
    *,
    registry: _HeaderRevisionRegistry,
    marker_counter: list[int],
) -> None:
    revisions = list(revisions)
    if not revisions:
        return
    new_blocks = _body_blocks(document)
    old_blocks = _body_blocks(old_document)

    for revision in revisions:
        if revision.kind != "insert":
            continue
        try:
            block = new_blocks[int(revision.new_block_index)]
        except IndexError as exc:
            raise DocumentUnsupportedError(
                "new HWPX paragraph moved while applying tracked insertion",
                code="compare-paragraph-alignment-ambiguous",
                context={"block_index": revision.new_block_index, "format": "hwpx"},
            ) from exc
        if not _is_paragraph_block(block):
            raise DocumentUnsupportedError(
                "tracked paragraph insertion no longer points to a paragraph",
                code="compare-paragraph-alignment-ambiguous",
                context={"block_index": revision.new_block_index, "format": "hwpx"},
            )
        _mark_whole_paragraph(
            block, kind="insert", registry=registry, marker_counter=marker_counter,
            block_index=int(revision.new_block_index),
        )

    offset = 0
    for revision in revisions:
        if revision.kind != "delete":
            continue
        source_index = revision.old_block_index
        if source_index is None:
            raise DocumentUnsupportedError(
                "deleted HWPX paragraph revision is missing its old source block",
                code="compare-paragraph-alignment-ambiguous",
            )
        try:
            source = old_blocks[int(source_index)]
        except IndexError as exc:
            raise DocumentUnsupportedError(
                "old HWPX paragraph moved while applying tracked deletion",
                code="compare-paragraph-alignment-ambiguous",
                context={"block_index": source_index, "format": "hwpx"},
            ) from exc
        if not _is_paragraph_block(source):
            raise DocumentUnsupportedError(
                "tracked HWPX paragraph deletion source is not a paragraph",
                code="compare-paragraph-alignment-ambiguous",
                context={"block_index": source_index, "format": "hwpx"},
            )
        _assert_structural_paragraph_safe(source, int(source_index))
        copied = _clone(source.element_model)
        copied.set("id", paragraph_id())
        copied.children[:] = [
            child for child in copied.children if local_name(child.tag) != "linesegarray"
        ]
        copied_paragraph = NativeParagraph(copied, document)
        _mark_whole_paragraph(
            copied_paragraph, kind="delete", registry=registry, marker_counter=marker_counter,
            block_index=int(source_index),
        )
        actual_index = int(revision.new_block_index) + offset
        _insert_body_paragraph(document, actual_index, copied)
        offset += 1


def _apply_format_revisions(
    document: Any, old_document: Any, plan: Any, *, registry: _HeaderRevisionRegistry,
) -> None:
    run_revisions = list(getattr(plan, "run_formats", ()))
    paragraph_revisions = list(getattr(plan, "paragraph_formats", ()))
    if not run_revisions and not paragraph_revisions:
        return
    output_paragraphs = _paragraphs(document, plan.everywhere)
    old_paragraphs = _paragraphs(old_document, plan.everywhere)

    target_indices = {int(r.paragraph_index) for r in run_revisions}
    target_indices.update(int(r.paragraph_index) for r in paragraph_revisions)
    for index in sorted(target_indices):
        try:
            _assert_no_existing_format_revision(output_paragraphs[index], index)
        except IndexError as exc:
            raise DocumentUnsupportedError(
                "paragraph alignment changed while applying HWPX formatting revisions",
                code="compare-format-map-failed",
                context={"paragraph_index": index, "format": "hwpx"},
            ) from exc

    for revision in paragraph_revisions:
        index = int(revision.paragraph_index)
        old_index = int(revision.old_paragraph_index)
        try:
            out_p = output_paragraphs[index]
            old_p = old_paragraphs[old_index]
        except IndexError as exc:
            raise DocumentUnsupportedError(
                "paragraph alignment changed while applying HWPX paragraph formatting revision",
                code="compare-format-map-failed",
                context={"paragraph_index": index, "old_paragraph_index": old_index, "format": "hwpx"},
            ) from exc
        # ParaShape revision metadata can restore paraPr but not an arbitrary
        # named style identity.  Raw style ids are header-local, so compare the
        # resolved named-style identity instead: equivalent styles may have
        # different local ids across unrelated documents, while equal numeric
        # ids may refer to different named styles.
        old_style_sig = _resolved_style_identity_signature(old_document, old_p.style_id_ref or "0")
        new_style_sig = _resolved_style_identity_signature(document, out_p.style_id_ref or "0")
        if new_style_sig != old_style_sig:
            raise DocumentUnsupportedError(
                "HWPX named paragraph-style changes are not representable by verified ParaShape tracking",
                code="compare-hwpx-style-reference-track-unsupported",
                context={
                    "paragraph_index": index,
                    "old_style_id": old_p.style_id_ref or "0",
                    "new_style_id": out_p.style_id_ref or "0",
                },
            )
        old_shape_id = _matching_old_property_id(
            document, old_document, kind="para", old_id=old_p.para_pr_id_ref,
        )
        change_id = registry.add_format("ParaShape", old_shape_id)
        out_p.element_model.set("paraTcId", str(change_id))
        out_p._clear_layout_cache()

    for revision in run_revisions:
        index = int(revision.paragraph_index)
        old_index = int(revision.old_paragraph_index)
        try:
            out_p = output_paragraphs[index]
            old_p = old_paragraphs[old_index]
        except IndexError as exc:
            raise DocumentUnsupportedError(
                "paragraph alignment changed while applying HWPX run formatting revision",
                code="compare-format-map-failed",
                context={"paragraph_index": index, "old_paragraph_index": old_index, "format": "hwpx"},
            ) from exc
        old_run = _run_for_range(old_p, old_index, int(revision.old_start), int(revision.old_end))
        old_shape_id = _matching_old_property_id(
            document, old_document, kind="char", old_id=old_run.get("charPrIDRef") or "0",
        )
        change_id = registry.add_format("CharShape", old_shape_id)
        _mark_char_format_range(
            out_p, index, int(revision.new_start), int(revision.new_end), change_id=change_id,
        )


def apply_revision_plan(document: Any, plan: Any, old_document: Any, *, author: str, date: str | None) -> None:
    if getattr(plan, "table_rows", ()):
        raise DocumentUnsupportedError(
            "HWPX table-row Track Changes has no verified native row anchor",
            code="compare-hwpx-table-row-track-unsupported",
            context={
                "verified_track_change_types": ["Insert", "Delete", "CharShape", "ParaShape"],
                "public_insert_delete_marker_scope": "hp:t mixed content",
                "verified_hp_tr_revision_anchor": False,
            },
            suggestion="analyze a Hancom-authored unaccepted row-change HWPX before enabling structural row revisions",
        )
    run_formats = tuple(getattr(plan, "run_formats", ()))
    paragraph_formats = tuple(getattr(plan, "paragraph_formats", ()))
    # v0.36.0: Hancom's public OWPML model writes paragraph-format revision
    # anchors as hp:p@paraTcId and the header TrackChange as type=ParaShape
    # with parashapeID=<old paraPr id>.  Keep named-style identity changes and
    # missing OLD paraPr resources fail-closed; plain paraPr changes can use the
    # verified model contract.
    if (
        not plan.paragraphs
        and not getattr(plan, "body_paragraphs", ())
        and not run_formats
        and not paragraph_formats
    ):
        return
    output_paragraphs = _paragraphs(document, plan.everywhere)
    old_paragraphs = _paragraphs(old_document, plan.everywhere)
    registry = _HeaderRevisionRegistry(document, author, date)
    marker_counter = [_numeric_max(document, {"insertBegin", "insertEnd", "deleteBegin", "deleteEnd"}, "Id") + 1]

    # Apply format anchors before text rebuilding. Hancom 2020 native CharShape
    # tracking stores the change id as run@paraTcId; the text writer copies run
    # attributes, so that anchor survives equal-text slices in mixed revisions.
    _apply_format_revisions(document, old_document, plan, registry=registry)
    output_paragraphs = _paragraphs(document, plan.everywhere)

    for revision in plan.paragraphs:
        index = revision.paragraph_index
        old_index = getattr(revision, "source_paragraph_index", index)
        try:
            out_p = output_paragraphs[index]
            old_p = old_paragraphs[old_index]
        except IndexError as exc:
            raise DocumentUnsupportedError(
                "paragraph alignment changed while applying HWPX revisions",
                code="compare-structural-change-not-supported",
                context={"paragraph_index": index, "format": "hwpx"},
            ) from exc
        _visible_runs(out_p, index)
        _visible_runs(old_p, old_index)

        structural_runs = [
            _clone(child)
            for child in out_p.element_model.children
            if local_name(child.tag) == "run"
            and not any(local_name(n.tag) == "t" for n in child.children)
        ]
        rebuilt: list[ElementModel] = list(structural_runs)

        for edit in revision.edits:
            if edit.tag == "equal":
                rebuilt.extend(_slice_runs(out_p, index, edit.new_start, edit.new_end))
            elif edit.tag == "insert":
                change_id = registry.add("insert")
                rebuilt.extend(_slice_runs(
                    out_p, index, edit.new_start, edit.new_end,
                    kind="insert", marker_counter=marker_counter, change_id=change_id,
                ))
            elif edit.tag == "delete":
                change_id = registry.add("delete")
                rebuilt.extend(_slice_runs(
                    old_p, old_index, edit.old_start, edit.old_end,
                    kind="delete", marker_counter=marker_counter, change_id=change_id,
                ))
            elif edit.tag == "replace":
                delete_id = registry.add("delete")
                rebuilt.extend(_slice_runs(
                    old_p, old_index, edit.old_start, edit.old_end,
                    kind="delete", marker_counter=marker_counter, change_id=delete_id,
                ))
                insert_id = registry.add("insert")
                rebuilt.extend(_slice_runs(
                    out_p, index, edit.new_start, edit.new_end,
                    kind="insert", marker_counter=marker_counter, change_id=insert_id,
                ))
            else:  # pragma: no cover - defensive
                raise ValueError(edit.tag)

        out_p.element_model.children[:] = rebuilt
        out_p._clear_layout_cache()

    _apply_body_paragraph_revisions(
        document,
        old_document,
        getattr(plan, "body_paragraphs", ()),
        registry=registry,
        marker_counter=marker_counter,
    )


__all__ = ["apply_revision_plan"]
