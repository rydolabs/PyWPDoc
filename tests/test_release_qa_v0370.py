"""v0.37.0 cross-document ParaShape release-QA integrity."""
from pathlib import Path
import hashlib, json
from zipfile import ZipFile

from lxml import etree
from pywpdoc._engine import validate_hwpx_file

ROOT=Path(__file__).resolve().parents[1]
HH="http://www.hancom.co.kr/hwpml/2011/head"; HP="http://www.hancom.co.kr/hwpml/2011/paragraph"; NS={"hh":HH,"hp":HP}


def test_v0370_crossdoc_parashape_manifest_and_files_are_consistent():
    idx=json.loads((ROOT/'docs/maintainers/QA_INDEX_V0370.json').read_text(encoding="utf-8"))
    assert idx['release']=='0.37.0-candidate'
    item=idx['scenarios'][0]
    d=ROOT/'tests/fixtures/historical'/item['directory']; m=json.loads((d/'manifest.json').read_text(encoding="utf-8"))
    assert m['scenario_id']==item['scenario_id']
    assert m['status']=='external-hancom-2020-gui-gate-pending'
    for role in ('old','new','tracked'):
        p=d/m[role]['file']; assert p.exists()
        assert hashlib.sha256(p.read_bytes()).hexdigest()==m[role]['sha256']
        assert validate_hwpx_file(p).ok


def test_v0370_crossdoc_parashape_review_remaps_numbering_and_bullet_resources():
    d=ROOT/'tests/fixtures/historical/qa_hwpx_cross_document_parashape_v0370'; m=json.loads((d/'manifest.json').read_text(encoding="utf-8")); p=d/m['tracked']['file']
    with ZipFile(p) as z:
        h=etree.fromstring(z.read('Contents/header.xml')); s=etree.fromstring(z.read('Contents/section0.xml'))
    changes=h.xpath('.//hh:trackChange[@type="ParaShape"]',namespaces=NS)
    assert len(changes)==m['expected']['count']==3
    assert len(s.xpath('.//hp:p[@paraTcId]',namespaces=NS))==3
    assert not s.xpath('.//hp:run[@paraTcId or @charTcId]',namespaces=NS)
    assert not s.xpath('.//hp:insertBegin | .//hp:insertEnd | .//hp:deleteBegin | .//hp:deleteEnd',namespaces=NS)

    by_text={case['text']:case for case in m['cases']}
    num=by_text['Numbering resource: Gamma Delta']
    assert num['old_heading']['idRef'] != num['new_heading']['idRef']
    assert h.xpath(f'.//hh:numbering[@id="{num["old_heading"]["idRef"]}"]/@start',namespaces=NS)==['3']
    assert h.xpath(f'.//hh:numbering[@id="{num["new_heading"]["idRef"]}"]/@start',namespaces=NS)==['7']

    bullet=by_text['Bullet resource: Sample Text']
    assert bullet['old_heading']['idRef'] != bullet['new_heading']['idRef']
    assert h.xpath(f'.//hh:bullet[@id="{bullet["old_heading"]["idRef"]}"]/@char',namespaces=NS)==['◈']
    assert h.xpath(f'.//hh:bullet[@id="{bullet["new_heading"]["idRef"]}"]/@char',namespaces=NS)==['•']
