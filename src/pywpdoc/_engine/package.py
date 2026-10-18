from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import io
import zipfile


@dataclass
class PackageEntryInfo:
    name: str
    compress_type: int
    date_time: tuple[int, int, int, int, int, int]
    comment: bytes = b""
    extra: bytes = b""
    internal_attr: int = 0
    external_attr: int = 0
    create_system: int = 3
    create_version: int = 20
    extract_version: int = 20
    flag_bits: int = 0


class HwpxPackage:
    def __init__(self, raw: bytes):
        self.parts: dict[str, bytes] = {}
        self.infos: dict[str, PackageEntryInfo] = {}
        self.order: list[str] = []
        with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
            for i in zf.infolist():
                self.order.append(i.filename)
                self.parts[i.filename] = zf.read(i.filename)
                self.infos[i.filename] = PackageEntryInfo(
                    i.filename, i.compress_type, i.date_time, i.comment, i.extra,
                    i.internal_attr, i.external_attr, i.create_system,
                    i.create_version, i.extract_version, i.flag_bits,
                )

    @classmethod
    def open(cls, path: str | Path) -> "HwpxPackage":
        return cls(Path(path).read_bytes())

    def set(self, name: str, data: bytes, info: PackageEntryInfo | None = None) -> None:
        if name not in self.order:
            self.order.append(name)
        self.parts[name] = data
        if info is not None:
            self.infos[name] = info
        elif name not in self.infos:
            self.infos[name] = PackageEntryInfo(name, zipfile.ZIP_DEFLATED, (2026,1,1,0,0,0))

    def remove(self, name: str) -> None:
        self.parts.pop(name, None)
        self.infos.pop(name, None)
        if name in self.order:
            self.order.remove(name)

    def reorder(self, names: list[str]) -> None:
        known = [n for n in names if n in self.parts]
        tail = [n for n in self.order if n not in known]
        self.order = known + tail

    def to_bytes(self) -> bytes:
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as zf:
            for name in self.order:
                if name not in self.parts:
                    continue
                meta = self.infos[name]
                info = zipfile.ZipInfo(name, meta.date_time)
                info.compress_type = meta.compress_type
                info.comment = meta.comment
                info.extra = meta.extra
                info.internal_attr = meta.internal_attr
                info.external_attr = meta.external_attr
                info.create_system = meta.create_system
                info.create_version = meta.create_version
                info.extract_version = meta.extract_version
                info.flag_bits = meta.flag_bits
                zf.writestr(info, self.parts[name])
        return out.getvalue()

    def save(self, path: str | Path) -> None:
        Path(path).write_bytes(self.to_bytes())
