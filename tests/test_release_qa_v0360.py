"""v0.36.0 ParaShape candidate release QA integrity."""
from pathlib import Path
import hashlib, json
from zipfile import ZipFile

from lxml import etree
from pywpdoc._engine import validate_hwpx_file

ROOT=Path(__file__).resolve().parents[1]
HH="http://www.hancom.co.kr/hwpml/2011/head"; HP="http://www.hancom.co.kr/hwpml/2011/paragraph"; NS={"hh":HH,"hp":HP}


def test_v0360_parashape_qa_manifest_and_files_are_consistent():
    idx=json.loads((ROOT/'docs/maintainers/QA_INDEX_V0360.json').read_text())
    assert idx['release']=='0.36.0-candidate'
    item=idx['scenarios'][0]
    d=ROOT/'tests/fixtures/historical'/item['directory']; m=json.loads((d/'manifest.json').read_text())
    assert m['scenario_id']==item['scenario_id']
    assert m['status']=='external-hancom-2020-gui-gate-pending'
    for role in ('old','new','tracked'):
        p=d/m[role]['file']; assert p.exists()
        assert hashlib.sha256(p.read_bytes()).hexdigest()==m[role]['sha256']
        assert validate_hwpx_file(p).ok


def test_v0360_parashape_tracked_review_has_only_paragraph_format_revisions():
    d=ROOT/'tests/fixtures/historical/qa_hwpx_parashape_v0360'; m=json.loads((d/'manifest.json').read_text()); p=d/m['tracked']['file']
    with ZipFile(p) as z:
        h=etree.fromstring(z.read('Contents/header.xml')); s=etree.fromstring(z.read('Contents/section0.xml'))
    changes=h.xpath('.//hh:trackChange[@type="ParaShape"]',namespaces=NS)
    assert len(changes)==m['expected']['count']==3
    assert not h.xpath('.//hh:trackChange[@type="CharShape" or @type="Insert" or @type="Delete"]',namespaces=NS)
    paras=s.xpath('.//hp:p[@paraTcId]',namespaces=NS)
    assert len(paras)==3
    assert not s.xpath('.//hp:run[@paraTcId or @charTcId]',namespaces=NS)
    assert not s.xpath('.//hp:insertBegin | .//hp:insertEnd | .//hp:deleteBegin | .//hp:deleteEnd',namespaces=NS)
    for para in paras:
        cid=para.get('paraTcId')
        change=h.xpath(f'.//hh:trackChange[@id="{cid}"]',namespaces=NS)
        assert len(change)==1 and change[0].get('parashapeID') is not None
        assert change[0].get('paraShapeID') is None
        assert para.get('paraPrIDRef') != change[0].get('parashapeID')
