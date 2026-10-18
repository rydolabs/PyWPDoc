from __future__ import annotations

from datetime import datetime, timezone

from .model import ElementModel, local_name

OPF_NS = "http://www.idpf.org/2007/opf/"
OPF = f"{{{OPF_NS}}}"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    try:
        if text.endswith("Z"):
            return datetime.fromisoformat(text[:-1] + "+00:00").replace(tzinfo=None)
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    if not isinstance(value, datetime):
        raise TypeError("metadata date value must be datetime or None")
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


class CoreProperties:
    """python-docx-shaped facade over ``Contents/content.hpf`` metadata.

    Only properties with measured HWPX counterparts are exposed as writable.
    Unknown metadata nodes remain untouched in the underlying ElementModel.
    """

    _META_NAMES = {
        "author": "creator",
        "subject": "subject",
        "comments": "description",
        "last_modified_by": "lastsaveby",
        "keywords": "keyword",
        "created": "CreatedDate",
        "modified": "ModifiedDate",
    }

    def __init__(self, document):
        self._document = document

    @property
    def element_model(self) -> ElementModel:
        return self._metadata()

    def _metadata(self) -> ElementModel:
        root = self._document.content_model
        node = next((c for c in root.children if local_name(c.tag) == "metadata"), None)
        if node is None:
            node = ElementModel(OPF + "metadata")
            root.children.insert(0, node)
        return node

    def _direct(self, name: str) -> ElementModel | None:
        return next((c for c in self._metadata().children if local_name(c.tag) == name), None)

    def _get_direct_text(self, name: str) -> str:
        node = self._direct(name)
        return "" if node is None else (node.text or "")

    def _set_direct_text(self, name: str, value: str | None) -> None:
        node = self._direct(name)
        if node is None:
            node = ElementModel(OPF + name)
            self._metadata().children.append(node)
        node.text = "" if value is None else str(value)

    def _meta(self, name: str) -> ElementModel | None:
        return next(
            (c for c in self._metadata().children if local_name(c.tag) == "meta" and c.get("name") == name),
            None,
        )

    def _get_meta_text(self, name: str) -> str:
        node = self._meta(name)
        return "" if node is None else (node.text or "")

    def _set_meta_text(self, name: str, value: str | None) -> None:
        node = self._meta(name)
        if node is None:
            node = ElementModel(OPF + "meta", attrs=[("name", name), ("content", "text")])
            self._metadata().children.append(node)
        elif node.get("content") is None:
            node.set("content", "text")
        node.text = "" if value is None else str(value)

    title = property(lambda s: s._get_direct_text("title"), lambda s, v: s._set_direct_text("title", v))
    language = property(lambda s: s._get_direct_text("language"), lambda s, v: s._set_direct_text("language", v))
    author = property(lambda s: s._get_meta_text("creator"), lambda s, v: s._set_meta_text("creator", v))
    subject = property(lambda s: s._get_meta_text("subject"), lambda s, v: s._set_meta_text("subject", v))
    comments = property(lambda s: s._get_meta_text("description"), lambda s, v: s._set_meta_text("description", v))
    last_modified_by = property(lambda s: s._get_meta_text("lastsaveby"), lambda s, v: s._set_meta_text("lastsaveby", v))
    keywords = property(lambda s: s._get_meta_text("keyword"), lambda s, v: s._set_meta_text("keyword", v))

    @property
    def created(self) -> datetime | None:
        return _parse_datetime(self._get_meta_text("CreatedDate"))

    @created.setter
    def created(self, value: datetime | None) -> None:
        self._set_meta_text("CreatedDate", _format_datetime(value))

    @property
    def modified(self) -> datetime | None:
        return _parse_datetime(self._get_meta_text("ModifiedDate"))

    @modified.setter
    def modified(self, value: datetime | None) -> None:
        self._set_meta_text("ModifiedDate", _format_datetime(value))


class CaretPosition:
    def __init__(self, settings: "Settings", model: ElementModel):
        self._settings = settings
        self._model = model

    @property
    def list_id_ref(self) -> int:
        return int(self._model.get("listIDRef", "0") or 0)

    @list_id_ref.setter
    def list_id_ref(self, value: int) -> None:
        self._model.set("listIDRef", str(int(value)))

    @property
    def para_id_ref(self) -> int:
        return int(self._model.get("paraIDRef", "0") or 0)

    @para_id_ref.setter
    def para_id_ref(self, value: int) -> None:
        self._model.set("paraIDRef", str(int(value)))

    @property
    def pos(self) -> int:
        return int(self._model.get("pos", "0") or 0)

    @pos.setter
    def pos(self, value: int) -> None:
        self._model.set("pos", str(int(value)))


class Settings:
    """Typed foundation over ``settings.xml`` without inventing DOCX-only semantics."""

    def __init__(self, document):
        self._document = document
        raw = document._package.parts.get("settings.xml")
        if raw is None:
            raise ValueError("HWPX package has no settings.xml")
        from .document import _parse_xml
        self._model = _parse_xml(raw)
        self._capture_baseline()

    @property
    def element_model(self) -> ElementModel:
        return self._model

    @property
    def caret_position(self) -> CaretPosition:
        node = next((c for c in self._model.children if local_name(c.tag) == "CaretPosition"), None)
        if node is None:
            node = ElementModel(
                "{http://www.hancom.co.kr/hwpml/2011/app}CaretPosition",
                attrs=[("listIDRef", "0"), ("paraIDRef", "0"), ("pos", "0")],
            )
            self._model.children.insert(0, node)
        return CaretPosition(self, node)

    def _capture_baseline(self) -> None:
        self._baseline_model = self._model.to_dict()

    def _sync_to_package(self) -> None:
        if self._model.to_dict() == getattr(self, "_baseline_model", None):
            return
        from .document import _xml_bytes
        self._document._package.set("settings.xml", _xml_bytes(self._model))
