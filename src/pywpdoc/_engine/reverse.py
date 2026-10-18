from __future__ import annotations

from pathlib import Path
from typing import Any
from lxml import etree
import base64
import hashlib
import json
import re
import zipfile

from .model import ElementModel, local_name


XML_SUFFIXES = (".xml", ".hpf", ".rdf")
_SECTION_RE = re.compile(r"^Contents/section(\d+)\.xml$")


def _entry_metadata(info: zipfile.ZipInfo) -> dict[str, Any]:
    return {
        "name": info.filename,
        "compress_type": info.compress_type,
        "date_time": list(info.date_time),
        "comment_b64": base64.b64encode(info.comment).decode("ascii"),
        "extra_b64": base64.b64encode(info.extra).decode("ascii"),
        "internal_attr": info.internal_attr,
        "external_attr": info.external_attr,
        "create_system": info.create_system,
        "create_version": info.create_version,
        "extract_version": info.extract_version,
        "flag_bits": info.flag_bits,
    }


def _xml_model(raw: bytes) -> ElementModel:
    parser = etree.XMLParser(remove_blank_text=False, remove_comments=False, remove_pis=False)
    return ElementModel.from_element(etree.fromstring(raw, parser), root=True)


def reverse_hwpx(source: str | Path, output_dir: str | Path) -> Path:
    """Reverse an HWPX into a lossless typed model + external binary assets."""
    source = Path(source)
    output_dir = Path(output_dir)
    assets = output_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    package_entries: list[dict[str, Any]] = []
    section_models: list[tuple[int, ElementModel]] = []
    header_model: ElementModel | None = None

    with zipfile.ZipFile(source, "r") as zf:
        for info in zf.infolist():
            raw = zf.read(info.filename)
            item = _entry_metadata(info)
            item["sha256"] = hashlib.sha256(raw).hexdigest()

            section_match = _SECTION_RE.match(info.filename)
            if section_match:
                index = int(section_match.group(1))
                section_models.append((index, _xml_model(raw)))
                item["kind"] = "document-section"
                item["section_index"] = index
            elif info.filename == "Contents/header.xml":
                header_model = _xml_model(raw)
                item["kind"] = "document-header"
            elif info.filename.endswith(XML_SUFFIXES):
                item["kind"] = "xml"
                item["model"] = _xml_model(raw).to_dict()
            else:
                if info.filename == "mimetype":
                    item["kind"] = "bytes"
                    item["data_b64"] = base64.b64encode(raw).decode("ascii")
                else:
                    safe_name = info.filename.replace("/", "__")
                    asset_path = assets / safe_name
                    asset_path.write_bytes(raw)
                    item["kind"] = "asset"
                    item["path"] = f"assets/{safe_name}"
            package_entries.append(item)

    section_models.sort(key=lambda item: item[0])
    if not section_models or header_model is None:
        raise ValueError("HWPX lacks Contents/section*.xml or Contents/header.xml")

    typed_names = {"p", "run", "tbl", "tr", "tc", "pic", "rect", "footNote", "endNote", "header", "footer", "bookmark", "fieldBegin", "fieldEnd", "t"}
    counts: dict[str, int] = {}
    oxml_counts: dict[str, int] = {}
    for _, section_model in section_models:
        for node in section_model.iter():
            name = local_name(node.tag)
            if name in typed_names:
                counts[name] = counts.get(name, 0) + 1
            else:
                oxml_counts[name] = oxml_counts.get(name, 0) + 1

    data = {
        "format": "python-hwpx-next-reverse-model",
        "version": 4,
        "source_name": source.name,
        "package": {"entries": package_entries},
        "document": {
            "header": {"model": header_model.to_dict()},
            "sections": [
                {"index": index, "model": model.to_dict()} for index, model in section_models
            ],
            # compatibility for consumers that only know a single section
            "section": {"model": section_models[0][1].to_dict()},
        },
        "coverage": {
            "typed": counts,
            "oxml_escape_hatch": oxml_counts,
        },
    }
    model_path = output_dir / "document_model.json"
    model_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return model_path


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Reverse an HWPX into a lossless typed model.")
    parser.add_argument("source")
    parser.add_argument("output_dir")
    args = parser.parse_args()
    print(reverse_hwpx(args.source, args.output_dir))


if __name__ == "__main__":
    main()
