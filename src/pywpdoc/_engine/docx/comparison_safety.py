"""Conservative DOCX fingerprints for content outside body-only revisions.

These are *not* revision markup: if an excluded visual/structural change cannot
be tracked, the compare feature must refuse to clone it silently.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from lxml import etree


def _xml(node):
    return etree.tostring(node, method="c14n")


def table_properties_signature(document):
    signature = []
    for table in document.iter_tables(everywhere=True):
        native = table.native._tbl
        props = []
        # Properties describe borders, fills, dimensions, cell merges,
        # table-level style, row layout, and cell alignment/margins.
        for child in native:
            tag = etree.QName(child).localname
            if tag in {"tblPr", "tblGrid"}:
                props.append((tag, _xml(child)))
            elif tag == "tr":
                row = []
                for cell in child:
                    kind = etree.QName(cell).localname
                    if kind == "trPr":
                        row.append((kind, _xml(cell)))
                    elif kind == "tc":
                        cell_properties = [
                            _xml(prop) for prop in cell
                            if etree.QName(prop).localname == "tcPr"
                        ]
                        row.append(("tc", tuple(cell_properties)))
                props.append(("tr", tuple(row)))
        signature.append(tuple(props))
    return tuple(signature)


def image_objects_signature(document):
    """Fingerprints for native drawings, including their referenced bytes.

    Comparing only the image count would miss changing a pixel, resizing,
    replacing, or moving an image in the resulting untracked clone.
    """
    output = []
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    volatile_names = {"id", "name", "descr", "title"}
    for part in document.native.part.package.parts:
        root = getattr(part, "element", None)
        if root is None:
            continue
        drawings = []
        for node in root.iter():
            if etree.QName(node).localname not in {"drawing", "pict", "object"}:
                continue
            # A whole object/anchor tree captures size and position changes.
            element = deepcopy(node)
            for child in element.iter():
                for attr, value in list(child.attrib.items()):
                    if attr.startswith("{" + rel_ns + "}"):
                        target = part.related_parts.get(value)
                        if target is None:
                            # External drawings cannot be verified safely.
                            child.set(attr, "external:" + str(value))
                        else:
                            child.set(attr, "sha256:" + sha256(target.blob).hexdigest())
                    elif (etree.QName(child).localname == "docPr"
                          and etree.QName(attr).localname in volatile_names):
                        child.set(attr, "<volatile>")
            drawings.append((root.getroottree().getpath(node), _xml(element)))
        if drawings:
            output.append((str(part.partname), tuple(drawings)))
    return tuple(sorted(output))
