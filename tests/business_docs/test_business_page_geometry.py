"""QA effective body geometry parity, not just raw page margins.

Persisted XML checks cannot prove native rendering parity; they only catch
regression in the fixture setup. Actual Word/Hancom PDF remains an external
visual gate.
"""
from __future__ import annotations

from zipfile import ZipFile

import pytest
from lxml import etree

from tests.generators.business_docs.scenarios import SCENARIOS, build_document

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
HP = 'http://www.hancom.co.kr/hwpml/2011/paragraph'


def _layout(path, fmt):
    with ZipFile(path) as z:
        if fmt == 'docx':
            root = etree.fromstring(z.read('word/document.xml'))
            ns = {'w': W}
            page = root.xpath('.//w:sectPr/w:pgSz', namespaces=ns)[-1]
            margin = root.xpath('.//w:sectPr/w:pgMar', namespaces=ns)[-1]
            return {
                'page_w': int(page.get(f'{{{W}}}w')) * 5,
                'page_h': int(page.get(f'{{{W}}}h')) * 5,
                'left': int(margin.get(f'{{{W}}}left')) * 5,
                'right': int(margin.get(f'{{{W}}}right')) * 5,
                'body_top': int(margin.get(f'{{{W}}}top')) * 5,
                'body_bottom': int(margin.get(f'{{{W}}}bottom')) * 5,
            }
        root = etree.fromstring(z.read('Contents/section0.xml'))
        ns = {'hp': HP}
        page = root.xpath('.//hp:pagePr', namespaces=ns)[0]
        margin = page.xpath('./hp:margin', namespaces=ns)[0]
        return {
            'page_w': int(page.get('width')),
            'page_h': int(page.get('height')),
            'left': int(margin.get('left')),
            'right': int(margin.get('right')),
            'body_top': int(margin.get('top')) + int(margin.get('header')),
            'body_bottom': int(margin.get('bottom')) + int(margin.get('footer')),
            'header': int(margin.get('header')),
            'footer': int(margin.get('footer')),
        }


@pytest.mark.common_api
@pytest.mark.parametrize('scenario_key', ['01_contract', '24_long_form'])
def test_business_qa_effective_body_margins_match_across_formats(scenario_key, tmp_path):
    scenario = next(s for s in SCENARIOS if s.key == scenario_key)
    dimensions = {}
    for fmt in ('docx', 'hwpx'):
        doc, _ = build_document(scenario, fmt)
        path = tmp_path / f'{scenario_key}.{fmt}'
        doc.save(path)
        dimensions[fmt] = _layout(path, fmt)
    a, b = dimensions['docx'], dimensions['hwpx']
    for key in ['page_w', 'page_h', 'left', 'right', 'body_top', 'body_bottom']:
        assert abs(a[key] - b[key]) <= 5, (key, a[key], b[key])
    assert b['header'] == b['footer'] == 0
