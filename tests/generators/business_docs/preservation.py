"""Strict text/media data preservation checks for DOCX Word COM round-trips."""
from __future__ import annotations
from collections import Counter
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def _docx_payload(path: Path) -> tuple[str, Counter]:
    with ZipFile(path) as package:
        document = ET.fromstring(package.read('word/document.xml'))
        text = ''.join((node.text or '') for node in document.iter(f'{W}t'))
        images = Counter(hashlib.sha256(package.read(name)).hexdigest()
                         for name in package.namelist() if name.startswith('word/media/')
                         and not name.endswith('/'))
    return text, images


def assert_docx_preserved(original: Path, resaved: Path) -> dict:
    """Require matching body text and embedded image content; fail, don't warn."""
    original_text, original_media = _docx_payload(original)
    resaved_text, resaved_media = _docx_payload(resaved)
    assert original_text == resaved_text, 'Word resave changed w:t body text or order'
    assert original_media == resaved_media, 'Word resave changed embedded media data'
    return {'body_text_equal': True, 'image_bytes_equal': True,
            'body_text_length': len(original_text), 'media_count': sum(original_media.values())}
