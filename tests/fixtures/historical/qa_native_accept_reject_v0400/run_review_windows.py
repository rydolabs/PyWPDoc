# -*- coding: utf-8 -*-
"""Native Hancom Windows COM approve-all / reject-all verification runner.

Requires an installed and licensed Hancom HWP. The actions were identified in
Hancom Action Table (2025 listing) but have NOT been exercised on HWP 2020 here.
Every branch opens a separate temporary *copy* of the immutable tracked source.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import traceback
from zipfile import ZipFile, ZIP_DEFLATED

from verify_review_hwpx import inspect_hwpx, preflight, compare_review, sha256

BASE_DIR=Path(__file__).resolve().parent
SOURCE=BASE_DIR/'SOURCE_TRACKED_V22.hwpx'
BASE=BASE_DIR/'BASE_BEFORE_EDIT.hwpx'
ACTIONS=(('accept','TrackChangeApplyAll'),('reject','TrackChangeCancelAll'))


def _json_safe(value):
    if value is None or isinstance(value,(bool,int,float,str)):
        return value
    return repr(value)


def make_zip(target:Path, workdir:Path)->None:
    with ZipFile(target,'w',ZIP_DEFLATED) as z:
        for p in sorted(workdir.rglob('*')):
            if p.is_file() and p!=target:
                z.write(p, p.relative_to(workdir).as_posix())


class HwpSession:
    def __init__(self):
        try:
            import win32com.client as win32
        except ImportError as exc:
            raise RuntimeError('pywin32 필요: py -3 -m pip install pywin32') from exc
        # Never attach to an existing user's HWP process; create an isolated one.
        self.hwp=win32.DispatchEx('HWPFrame.HwpObject')
        self.hwp.XHwpWindows.Item(0).Visible=True

    def open(self,source:Path)->None:
        # Discard unsaved changes; this only touches the automation instance.
        self.hwp.Clear(1)
        result=self.hwp.Open(str(source.resolve()),'HWPX','')
        if result is False:
            raise RuntimeError(f'한글 파일 열기 실패: {source}')

    def run(self,action:str):
        # HAction.Run may return False even when a revision action took effect.
        # Only the independently saved HWPX can establish the result.
        return self.hwp.HAction.Run(action)

    def save(self,target:Path):
        if target.exists():
            target.unlink()
        result=self.hwp.SaveAs(str(target.resolve()),'HWPX','')
        if not target.is_file() or target.stat().st_size==0:
            raise RuntimeError(f'저장된 파일이 없음: {target}; SaveAs return={result!r}')
        return result

    def close(self)->None:
        try: self.hwp.Clear(1)
        except Exception: pass
        try: self.hwp.Quit()
        except Exception: pass


def run(workdir:Path,driver_factory=HwpSession)->dict:
    workdir.mkdir(parents=True,exist_ok=True)
    records=[]
    pre=None
    src_before=sha256(SOURCE)
    try:
        pre=preflight(SOURCE,BASE)
        if pre['status']!='PASS':
            raise RuntimeError('입력 문서 검증 실패: '+', '.join(pre['errors']))
        source=inspect_hwpx(SOURCE)
    except Exception as exc:
        payload={'status':'ERROR','stage':'preflight','exception':repr(exc),'traceback':traceback.format_exc()}
        (workdir/'results.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
        return payload

    # Open a fresh input copy for each branch. A COM success is never a PASS by itself.
    for mode,action in ACTIONS:
        entry={'branch':mode,'action':action,'status':'ERROR','output':None}
        session=None
        try:
            branch_input=workdir/f'INPUT_{mode.upper()}_COPY.hwpx'
            shutil.copy2(SOURCE, branch_input)
            entry['input_sha256']=sha256(branch_input)
            if entry['input_sha256']!=src_before:
                raise RuntimeError('복사본 SHA-256 불일치')
            session=driver_factory()
            session.open(branch_input)
            action_result=session.run(action)
            entry['action_return']=_json_safe(action_result)
            entry['action_return_type']=type(action_result).__name__
            out=workdir/f'{mode.upper()}_ALL_NATIVE.hwpx'
            save_result=session.save(out)
            entry['save_return']=_json_safe(save_result)
            entry['output']=out.name
            after=inspect_hwpx(out)
            entry['output_sha256']=after['sha256']
            entry['review']=compare_review(source,after,mode)
            entry['status']=entry['review']['status']
            if action_result is False:
                entry['note']='HAction.Run False 반환; 실제 파일 검사 결과로 판정함'
        except Exception as exc:
            entry['error']=repr(exc)
            entry['traceback']=traceback.format_exc()
        finally:
            if session is not None:
                try:session.close()
                except Exception as exc:entry['cleanup_error']=repr(exc)
        records.append(entry)

    source_unchanged=sha256(SOURCE)==src_before
    final_status='PASS' if source_unchanged and all(r['status']=='PASS' for r in records) else 'REVIEW'
    report={'status':final_status,'generated_at_utc':datetime.now(timezone.utc).isoformat(),
            'source':'SOURCE_TRACKED_V22.hwpx','source_sha256':src_before,
            'source_unchanged':source_unchanged,'preflight':pre,
            'expected_results':'accept: ABCD/ABC/NEW, bold/center; reject: ABC/ABCD/OLD, plain/justify; structural tables unchanged',
            'branches':records,
            'warning':'액션 반환값 True/False 또는 저장만으로 통과 판정하지 않음. 파일의 내용과 미해결 마커를 검사함. 표 구조 revision 미지원 판단 유지.'}
    (workdir/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    with (workdir/'results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        wr=csv.writer(f);wr.writerow(['branch','test_case','status','message','observed','expected'])
        for entry in records:
            if entry.get('review'):
                for result in entry['review']['checks']:
                    wr.writerow([entry['branch'],result['case'],result['status'],result['message'],
                                 repr(result.get('observed')),repr(result.get('expected'))])
            else:
                wr.writerow([entry['branch'],'COM_ACTION',entry['status'],entry.get('error',''),'',''])
    readme=['# 한글 네이티브 변경 추적 승인·거부 배치 결과','',
            '- 원본 파일 SHA-256: `'+src_before+'`',
            '- 원본 불변 여부: '+str(source_unchanged),
            '- 총괄: **'+final_status+'**','']
    for ent in records:
        readme.append(f"## {ent['branch']} — {ent['status']}")
        readme.append(f"- 실행 액션: `{ent['action']}`")
        if 'action_return' in ent:
            readme.append(f"- HAction.Run 반환값: `{ent['action_return']!r}` ({ent['action_return_type']})")
        if 'save_return' in ent:
            readme.append(f"- SaveAs 반환값: `{ent['save_return']!r}`")
        if ent.get('note'):readme.append('- 판정 메모: '+ent['note'])
        if ent.get('error'):readme.append('- 오류: `'+ent['error']+'`')
        if ent.get('review'):
            ct=ent['review']['counts'];readme.append(f"- 검사: PASS {ct['passed']} / FAIL {ct['failed']}")
            readme.append('- 저장 파일: '+str(ent.get('output')))
            for item in ent['review']['checks']:
                if item['status']!='PASS':readme.append(f"- 실패 {item['case']}: {item['message']} — {item['observed']!r}")
        readme.append('')
    readme.extend(['## 판정 주의','각 분기의 전체 판정은 파일 구조와 실제 텍스트/서식을 함께 비교합니다.',
                   '표의 행·열·병합은 편집 결과가 보존되는지만 확인하며 추적 가능하다고 인정하지 않습니다.',
                   '원본과 분기별 입력 복사본을 보관하므로 재현 가능합니다.'])
    (workdir/'summary.md').write_text('\n'.join(readme)+'\n',encoding='utf-8')
    return report


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument('--output-dir',type=Path,default=BASE_DIR/'HWP_REVIEW_RESULTS')
    args=parser.parse_args()
    out=args.output_dir.resolve()
    try:
        report=run(out)
    except Exception as exc:
        report={'status':'ERROR','error':repr(exc),'traceback':traceback.format_exc()}
        out.mkdir(parents=True,exist_ok=True)
        (out/'fatal_error.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    zip_path=out/'HWP_REVIEW_RESULTS.zip'
    make_zip(zip_path,out)
    print('STATUS:',report['status'])
    print('RESULT:',zip_path)
    for item in report.get('branches',[]):
        print('BRANCH:',item['branch'],item['status'],item.get('error',''))
    # 0 only if fully verified. The BAT keeps the window open for inspection.
    return 0 if report['status']=='PASS' else 2


if __name__=='__main__':
    sys.exit(main())
