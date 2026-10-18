# -*- coding: utf-8 -*-
"""Read-only HWPX acceptance/rejection oracle for the native v2.2 sample.

Conservative: all verdicts require actual saved content, not action return codes.
Does not modify HWPX and cannot establish GUI rendering/visual equivalence.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

TEXT_EXPECTED = {
    "accept": {"T01_INSERT": "ABCD", "T02_DELETE": "ABC", "T03_REPLACE": "NEW"},
    "reject": {"T01_INSERT": "ABC", "T02_DELETE": "ABCD", "T03_REPLACE": "OLD"},
}
TARGETS = {"T01_INSERT", "T02_DELETE", "T03_REPLACE", "T04_CHAR", "T05_PARA"}
STRUCTURAL = {"S06_ROW_INSERT", "S07_ROW_DELETE", "S08_COL_INSERT", "S09_COL_DELETE", "S10_CELL_MERGE"}
ALL_CASES = TARGETS | STRUCTURAL
MARKERS = {"insertBegin", "insertEnd", "deleteBegin", "deleteEnd"}


def local(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _char_is_bold(char: ET.Element | None) -> bool | None:
    if char is None:
        return None
    # In the observed HWPX, the presence of <hh:bold/> is the bold flag.
    return any(local(child.tag) == 'bold' for child in char)


def _para_align(para: ET.Element | None) -> str | None:
    if para is None:
        return None
    for node in para:
        if local(node.tag) == 'align':
            return node.get('horizontal')
    return None


def _read_cell(cell: ET.Element, chars: dict, paras: dict) -> dict:
    paragraphs=[]
    for p in cell.iter():
        if local(p.tag) != 'p':
            continue
        segments=[]
        for run in p:
            if local(run.tag) != 'run':
                continue
            # HWPX stores revised characters as tails of insert/delete markers
            # nested *inside* hp:t. Element.itertext() retains these tails.
            txt=''.join(''.join(node.itertext()) for node in run if local(node.tag)=='t')
            if txt:
                segments.append({"text":txt,"bold":_char_is_bold(chars.get(run.get('charPrIDRef')))})
        paragraphs.append({
            'text': ''.join(seg['text'] for seg in segments),
            'alignment': _para_align(paras.get(p.get('paraPrIDRef'))),
            'segments': segments,
        })
    return {'text':'\n'.join(p['text'] for p in paragraphs), 'paragraphs':paragraphs}


def _span(cell: ET.Element) -> tuple[int,int]:
    for node in cell:
        if local(node.tag) == 'cellSpan':
            return int(node.get('colSpan','1')),int(node.get('rowSpan','1'))
    return (1,1)


def inspect_hwpx(path: Path) -> dict:
    path=Path(path)
    with ZipFile(path) as z:
        bad=z.testzip()
        if bad:
            raise ValueError('손상된 HWPX ZIP 멤버: '+bad)
        header=ET.fromstring(z.read('Contents/header.xml'))
        chars={node.get('id'):node for node in header.iter() if local(node.tag)=='charPr'}
        paras={node.get('id'):node for node in header.iter() if local(node.tag)=='paraPr'}
        revisions=[dict(node.attrib) for node in header.iter() if local(node.tag)=='trackChange']
        flags=next((node.get('flags') for node in header.iter() if local(node.tag)=='trackchageConfig'),None)
        tables={}
        count=0
        mark_count=0
        anchors=[]
        for name in sorted(n for n in z.namelist() if n.startswith('Contents/section') and n.endswith('.xml')):
            root=ET.fromstring(z.read(name))
            for node in root.iter():
                kind=local(node.tag)
                if kind in MARKERS:
                    mark_count+=1
                for attr in ('charTcId','paraTcId'):
                    if attr in node.attrib:
                        anchors.append((kind,attr,node.attrib[attr]))
                if kind!='tbl':
                    continue
                count+=1
                rows=[]
                spans=[]
                cell_detail=[]
                for tr in node:
                    if local(tr.tag)!='tr':
                        continue
                    cells=[c for c in tr if local(c.tag)=='tc']
                    details=[_read_cell(c, chars, paras) for c in cells]
                    rows.append([c['text'] for c in details])
                    spans.append([_span(c) for c in cells])
                    cell_detail.append(details)
                if not rows or not rows[0]:
                    continue
                case_id=rows[0][0].strip()
                if case_id in ALL_CASES:
                    if case_id in tables:
                        raise ValueError('중복 테스트 표: '+case_id)
                    tables[case_id]={
                        'rows':rows,
                        'spans':spans,
                        'cols':int(node.get('colCnt',str(max(map(len,rows))))),
                        'row_count':len(rows),
                        'cells':cell_detail,
                        'local_markers':[local(child.tag) for child in node.iter() if local(child.tag) in MARKERS],
                        'local_anchors':[(local(child.tag),a,child.attrib[a]) for child in node.iter()
                                          for a in ('charTcId','paraTcId') if a in child.attrib],
                    }
    return {'sha256':sha256(path),'tables':tables,'total_tables':count,'revision_markers':mark_count,
            'revision_anchors':anchors,'header_revisions':revisions,'flags':flags}


def _cell_detail(sample: dict, case: str) -> dict | None:
    rows=sample['tables'].get(case,{}).get('cells')
    if not rows or len(rows)<2 or len(rows[1])<2:
        return None
    return rows[1][1]


def compare_review(source: dict, result: dict, mode: str) -> dict:
    if mode not in TEXT_EXPECTED:
        raise ValueError('mode must be accept or reject')
    judgments=[]
    def add(case,ok,message,observed=None,expected=None):
        judgments.append({'case':case,'status':'PASS' if ok else 'FAIL','message':message,
                          'observed':observed,'expected':expected})
    source_tables=set(source['tables'])
    result_tables=set(result['tables'])
    add('P00_TABLES', result_tables==source_tables==ALL_CASES,
        '기준과 출력의 10개 테스트 표 ID 보존', sorted(result_tables),sorted(ALL_CASES))
    add('P01_UNRESOLVED',result['revision_markers']==0 and not result['revision_anchors'],
        '본문 revision 마커 및 anchor가 모두 해소돼야 함',
        {'markers':result['revision_markers'],'anchors':result['revision_anchors']}, {'markers':0,'anchors':[]})
    for case,expected in TEXT_EXPECTED[mode].items():
        details=_cell_detail(result,case)
        observed=details['text'] if details else None
        add(case, observed==expected,'승인/거부 후 실제 텍스트 확인',observed,expected)
    char=_cell_detail(result,'T04_CHAR')
    segs=char.get('paragraphs',[{}])[0].get('segments',[]) if char else []
    # Every run in this target must resolve to a definite boolean; a mixed
    # or unknown state must not incorrectly PASS rejection.
    expected_bold=(mode=='accept')
    observed_bold=([s['bold'] for s in segs] if segs else None)
    bold_ok=bool(segs) and all(s['bold'] is expected_bold for s in segs)
    add('T04_CHAR',bold_ok,'굵게 적용/원복 확인',observed_bold,[expected_bold]*len(segs) if segs else [expected_bold])
    para=_cell_detail(result,'T05_PARA')
    align=para.get('paragraphs',[{}])[0].get('alignment') if para else None
    original=_cell_detail(source,'T05_PARA')
    original_align=original.get('paragraphs',[{}])[0].get('alignment') if original else None
    expected_align='CENTER' if mode=='accept' else 'JUSTIFY'
    add('T05_PARA',align==expected_align,'문단 정렬 적용/원복 확인',align,expected_align)
    for case in sorted(STRUCTURAL):
        before=source['tables'].get(case)
        after=result['tables'].get(case)
        fields=('rows','spans','cols','row_count')
        observed={k:after[k] for k in fields} if after else None
        expected={k:before[k] for k in fields} if before else None
        add(case, observed==expected,'비추적 표 구조 편집 결과는 양쪽 분기에서 보존',observed,expected)
    # Header revision definitions are *not* necessarily removed on save;
    # don't silently treat their survival as success or failure.
    passed=all(item['status']=='PASS' for item in judgments)
    return {'mode':mode,'status':'PASS' if passed else 'FAIL','counts':{
                'passed':sum(i['status']=='PASS' for i in judgments),
                'failed':sum(i['status']=='FAIL' for i in judgments)},
            'header_revision_entries_after':len(result['header_revisions']),
            'header_revision_note':'참고 정보만 기록; 실제 해소 판정은 본문 마커와 내용 검증',
            'tracked_para_alignment':original_align,'checks':judgments}


def preflight(source_file: Path, baseline_file: Path) -> dict:
    source=inspect_hwpx(source_file)
    baseline=inspect_hwpx(baseline_file)
    errors=[]
    if set(source['tables'])!=ALL_CASES: errors.append('추적 입력본 테스트 표 10개가 아님')
    if set(baseline['tables'])!=ALL_CASES: errors.append('편집 이전 기준본 테스트 표 10개가 아님')
    if source['revision_markers']<6: errors.append('추적본에 예상한 삽입/삭제 마커가 부족')
    if len(source['header_revisions'])<6: errors.append('추적본 header 변경 이력 6건 미만')
    for case in STRUCTURAL:
        if source['tables'].get(case)==baseline['tables'].get(case):
            errors.append(f'표 구조 편집 {case} 변화가 확인되지 않음')
    expected_text={"T01_INSERT":"ABCD","T02_DELETE":"ABCD","T03_REPLACE":"OLDNEW"}
    expected_base={"T01_INSERT":"ABC","T02_DELETE":"ABCD","T03_REPLACE":"OLD"}
    for case in expected_text:
        source_cell=_cell_detail(source,case)
        baseline_cell=_cell_detail(baseline,case)
        if not source_cell or source_cell['text']!=expected_text[case]:
            errors.append(f'{case} 추적본 텍스트 불일치')
        if not baseline_cell or baseline_cell['text']!=expected_base[case]:
            errors.append(f'{case} 기준본 텍스트 불일치')
    for case,markers in {
        'T01_INSERT':{'insertBegin','insertEnd'},
        'T02_DELETE':{'deleteBegin','deleteEnd'},
        'T03_REPLACE':{'insertBegin','insertEnd','deleteBegin','deleteEnd'},
    }.items():
        present=set(source['tables'].get(case,{}).get('local_markers',[]))
        if not markers <= present:
            errors.append(f'{case} 필수 revision marker 누락')
    kinds={revision.get('id'):revision.get('type') for revision in source['header_revisions']}
    for case,expected_kind in [('T04_CHAR','CharShape'),('T05_PARA','ParaShape')]:
        anchors=source['tables'].get(case,{}).get('local_anchors',[])
        if not any(kinds.get(item[2])==expected_kind for item in anchors):
            errors.append(f'{case} revision anchor ↔ header 종류 매핑 누락')
    if _cell_detail(source,'T04_CHAR') is None or _cell_detail(source,'T05_PARA') is None:
        errors.append('서식 검증 대상 셀 누락')
    baseline_bold=_cell_detail(baseline,'T04_CHAR')
    if not baseline_bold or any(s['bold'] is not False for p in baseline_bold['paragraphs'] for s in p['segments']):
        errors.append('T04 기준본 글자 굵게 상태가 보통이 아님')
    baseline_para=_cell_detail(baseline,'T05_PARA')
    if not baseline_para or not baseline_para['paragraphs'] or baseline_para['paragraphs'][0]['alignment']!='JUSTIFY':
        errors.append('T05 기준본 문단 정렬이 JUSTIFY가 아님')
    return {'status':'PASS' if not errors else 'FAIL','errors':errors,'sha256':source['sha256'],
            'flags':source['flags'],'header_revisions':len(source['header_revisions']),
            'revision_markers':source['revision_markers'],'anchors':len(source['revision_anchors']),
            'tables':sorted(source['tables'])}


if __name__ == '__main__':
    import argparse,json
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('candidate',type=Path)
    parser.add_argument('--mode',choices=('accept','reject'),required=True)
    args=parser.parse_args()
    print(json.dumps(compare_review(inspect_hwpx(args.source),inspect_hwpx(args.candidate),args.mode),
                     ensure_ascii=False,indent=2))
