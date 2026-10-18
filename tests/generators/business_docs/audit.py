"""Independent archive checks, supplementing Common API semantic assertions."""
from __future__ import annotations
from pathlib import Path
import zipfile
from lxml import etree
from tests.generators.business_docs.scenarios import test_image_bytes

XML_ENDINGS = ('.xml', '.rels', '.hpf', '.rdf')


def audit_archive(path: Path, *, expect_image: bool = False) -> dict:
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None, f'CRC error in {path}'
        names = z.namelist()
        assert len(names) == len(set(names)), 'duplicate package part names'
        parsed = 0
        for name in names:
            if name.lower().endswith(XML_ENDINGS):
                etree.fromstring(z.read(name))
                parsed += 1
        assert parsed > 0
        fmt = path.suffix.lower()
        if fmt == '.docx':
            assert 'word/document.xml' in names
            media = [n for n in names if n.startswith('word/media/') and n.lower().endswith('.png')]
        elif fmt == '.hwpx':
            assert 'Contents/content.hpf' in names
            media = [n for n in names if n.startswith('BinData/') and n.lower().endswith('.png')]
        else:
            raise AssertionError('not DOCX/HWPX')
        if expect_image:
            assert media, f'expected inserted image absent: {path}'
            assert test_image_bytes() in [z.read(n) for n in media], 'embedded PNG changed'
        return {'members': len(names), 'parsed_xml': parsed, 'embedded_images': len(media), 'bytes': path.stat().st_size}
