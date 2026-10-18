"""Explicit cross-format formatting contract for the synthetic QA corpus.

Native Word/Hancom rendering still requires the separate Windows visual gate.
These assertions prevent a recurrence of the original source-level discrepancy.
"""
from __future__ import annotations

from zipfile import ZipFile

import pytest
from lxml import etree

from tests.generators.business_docs.scenarios import SCENARIOS, build_document

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
HH = 'http://www.hancom.co.kr/hwpml/2011/head'
HP = 'http://www.hancom.co.kr/hwpml/2011/paragraph'
HC = 'http://www.hancom.co.kr/hwpml/2011/core'


@pytest.mark.common_api
@pytest.mark.parametrize('fmt', ('docx', 'hwpx'))
def test_business_samples_use_explicit_comparable_paragraph_baseline(fmt, tmp_path):
    scenario = next(s for s in SCENARIOS if s.key == '01_contract')
    document, _ = build_document(scenario, fmt)
    target = tmp_path / f'contract.{fmt}'
    document.save(target)

    with ZipFile(target) as archive:
        if fmt == 'docx':
            ns = {'w': W}
            styles = etree.fromstring(archive.read('word/styles.xml'))
            body = etree.fromstring(archive.read('word/document.xml'))
            style = styles.xpath('//w:style[@w:styleId="Normal"]', namespaces=ns)[0]
            spacing = style.xpath('./w:pPr/w:spacing', namespaces=ns)[0]
            assert spacing.get(f'{{{W}}}before') == '0'
            assert spacing.get(f'{{{W}}}after') == '0'
            assert style.xpath('./w:rPr/w:sz/@w:val', namespaces=ns) == ['20']
            body_spacings = body.xpath('./w:body/w:p/w:pPr/w:spacing', namespaces=ns)
            assert len(body_spacings) >= 10
            assert all(node.get(f'{{{W}}}line') == '320' for node in body_spacings)
            assert all(node.get(f'{{{W}}}lineRule') == 'exact' for node in body_spacings)
        else:
            ns = {'hh': HH, 'hp': HP, 'hc': HC}
            head = etree.fromstring(archive.read('Contents/header.xml'))
            body = etree.fromstring(archive.read('Contents/section0.xml'))
            normal = head.xpath('//hh:styles/hh:style[@id="0"]', namespaces=ns)[0]
            pr_ref = normal.get('paraPrIDRef')
            char_ref = normal.get('charPrIDRef')
            props = head.xpath('//hh:paraProperties/hh:paraPr[@id=$ref]', namespaces=ns, ref=pr_ref)[0]
            char_props = head.xpath('//hh:charProperties/hh:charPr[@id=$ref]', namespaces=ns, ref=char_ref)[0]
            assert char_props.get('height') == '1000'
            assert props.xpath('./hh:lineSpacing/@value', namespaces=ns) == ['160']
            assert props.xpath('./hh:margin/hc:prev/@value', namespaces=ns) == ['0']
            assert props.xpath('./hh:margin/hc:next/@value', namespaces=ns) == ['0']
            refs = [p.get('paraPrIDRef') for p in body.xpath('./hp:p', namespaces=ns)]
            assert refs and set(refs) == {pr_ref}
