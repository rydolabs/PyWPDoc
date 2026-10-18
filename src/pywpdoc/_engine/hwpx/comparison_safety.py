"""Compare HWPX table geometry and visible properties, omitting generated IDs."""
from __future__ import annotations
from hashlib import sha256


def _attrs(node):
    return tuple(sorted((str(k), str(v)) for k, v in node.attrs
                        if str(k).lower() not in {"id", "instid"}))


def _layout(node):
    """Exclude ordinary cell text (already checked) and generated layout caches."""
    local = node.tag.rsplit("}", 1)[-1].lower()
    if local in {"sublist", "p", "linesegarray"}:
        return None
    children = tuple(x for c in node.children if (x := _layout(c)) is not None)
    return (node.tag, _attrs(node), children)


def table_properties_signature(document):
    return tuple(_layout(table.native._model)
                 for table in document.iter_tables(everywhere=True))


def image_objects_signature(document):
    """Stable visible image positions and dimensions, plus media references.

    HWPX image resources are compared by the native properties. Internal
    reference IDs may differ across independently authored packages, so only
    observable width/height and reference properties can be compared here.
    """
    result = []
    for picture in document.native.pictures:
        native = picture
        model = getattr(native, "_model", None)
        if model is None:
            # No stable native image representation: refuse by marking unknown.
            result.append(("unsupported-picture", repr(type(native))))
        else:
            result.append(_layout(model))
    # Only *visible picture objects* belong to this safety guard. Image
    # bullets are paragraph-format resources: their cross-document payload
    # remapping is a supported tracked ParaShape edit and must not be blocked.
    picture_refs = {pic.binary_item_id_ref for pic in document.native.pictures
                    if pic.binary_item_id_ref}
    manifest = {
        item.get("id"): item.get("href")
        for item in document.native.content_model.iter()
        if item.tag.rsplit("}", 1)[-1] == "item"
    }
    data = getattr(getattr(document.native, "_package", None), "parts", {})
    media = []
    for ref in sorted(picture_refs):
        href = manifest.get(ref)
        if href is None:
            media.append((ref, "missing-manifest"))
            continue
        blob = data.get(href)
        media.append((ref, sha256(blob).hexdigest() if blob is not None else "missing-payload"))
    return (tuple(result), tuple(media))
