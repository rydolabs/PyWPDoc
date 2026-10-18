"""v0.35.0 release QA integrity."""
from pathlib import Path
import json, hashlib
from zipfile import ZipFile
from lxml import etree
from pywpdoc._engine import validate_hwpx_file

ROOT=Path(__file__).resolve().parents[1]
HH="http://www.hancom.co.kr/hwpml/2011/head"; HP="http://www.hancom.co.kr/hwpml/2011/paragraph"; NS={"hh":HH,"hp":HP}

def test_v0350_cross_document_qa_is_self_consistent():
    idx=json.loads((ROOT/'docs/maintainers/QA_INDEX_V0350.json').read_text())
    assert idx['release']=='0.35.0'
    item=idx['scenarios'][0]; d=ROOT/'tests/fixtures/historical'/item['directory']; m=json.loads((d/'manifest.json').read_text())
    assert m['scenario_id']==item['scenario_id']
    for role in ('old','new','tracked'):
        p=d/m[role]['file']; assert p.exists(); assert hashlib.sha256(p.read_bytes()).hexdigest()==m[role]['sha256']; assert validate_hwpx_file(p).ok

def test_v0350_tracked_review_contains_resolved_old_and_new_fonts():
    d=ROOT/'tests/fixtures/historical/qa_hwpx_cross_document_char_format_v0350'; m=json.loads((d/'manifest.json').read_text()); p=d/m['tracked']['file']
    with ZipFile(p) as z:
        h=etree.fromstring(z.read('Contents/header.xml')); s=etree.fromstring(z.read('Contents/section0.xml'))
    c=h.xpath('.//hh:trackChange[@type="CharShape"]',namespaces=NS)[0]
    run=s.xpath('.//hp:run[hp:t="Alpha Beta"]',namespaces=NS)[0]
    assert run.get('paraTcId')==c.get('id') and run.get('charTcId') is None
    oldcp=h.xpath(f'.//hh:charPr[@id="{c.get("charshapeID")}"]',namespaces=NS)[0]
    newcp=h.xpath(f'.//hh:charPr[@id="{run.get("charPrIDRef")}"]',namespaces=NS)[0]
    def faces(cp):
        ref=cp.xpath('./hh:fontRef',namespaces=NS)[0]; out=set()
        for lang,attr in [('HANGUL','hangul'),('LATIN','latin'),('HANJA','hanja'),('JAPANESE','japanese'),('OTHER','other'),('SYMBOL','symbol'),('USER','user')]:
            f=h.xpath(f'.//hh:fontface[@lang="{lang}"]/hh:font[@id="{ref.get(attr)}"]',namespaces=NS); assert len(f)==1; out.add(f[0].get('face'))
        return out
    assert faces(oldcp)=={m['old_font']}; assert faces(newcp)=={m['new_font']}
