"""Generate 8x2 merged-grid documents, roundtrip each through real native editors.

Runs every case separately and always produces a ZIP (including failures).
Use --generate-only on Linux to verify the generator without claiming COM results.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile,ZIP_DEFLATED
from tests.generators.business_docs.merge_grid import CASES, build_case, check_common_api


def generate(out:Path,formats:tuple[str,...],only:set[str]|None=None)->list[dict]:
    out.mkdir(parents=True,exist_ok=True)
    results=[]
    for case in CASES:
        if only and case.key not in only:continue
        for fmt in formats:
            p=out/f'{case.key}.{fmt}'
            record={'id':case.key,'format':fmt,'filename':p.name}
            try:
                build_case(case,fmt).save(p)
                record['structure']=check_common_api(p,case)
                record['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
                record['status']='PASS'
            except Exception as error:
                record['status']='FAIL'
                record['error']=repr(error)
            results.append(record)
            print(f'GENERATE {record["status"]} {p.name}',flush=True)
    (out/'merge_inputs.json').write_text(json.dumps({'cases':results},ensure_ascii=False,indent=2),encoding='utf-8')
    return results


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,default=Path('merge_grid_native_results'))
    parser.add_argument('--format',choices=('both','docx','hwpx'),default='both')
    parser.add_argument('--only',nargs='*',default=[])
    parser.add_argument('--timeout',type=int,default=240)
    parser.add_argument('--generate-only',action='store_true')
    a=parser.parse_args()
    formats=('docx','hwpx') if a.format=='both' else (a.format,)
    entries=generate(a.out/'generated',formats,set(a.only) if a.only else None)
    results=[]
    if not a.generate_only:
        for e in entries:
            if e['status']!='PASS':
                results.append({**e,'native_status':'NOT_TESTED','error':'generation failed'})
                continue
            source=a.out/'generated'/e['filename']
            output=a.out/'resaved'/e['filename']
            pdf=a.out/'pdf'/f'{e["id"]}-{e["format"]}.pdf'
            command=[sys.executable,'-m','tests.generators.business_docs.windows_merged_grid_worker',
                     '--source',str(source),'--output',str(output),'--pdf',str(pdf)]
            try:
                execution=subprocess.run(command,text=True,capture_output=True,timeout=a.timeout)
                try:
                    result=json.loads(execution.stdout.strip().splitlines()[-1])
                except (IndexError,ValueError):
                    result={'status':'FAIL','error':'worker emitted no valid result',
                            'stdout':execution.stdout[-2000:]}
                if execution.returncode!=0: result['status']='FAIL'
                if execution.stderr:result['stderr']=execution.stderr[-2000:]
            except subprocess.TimeoutExpired:
                result={'status':'FAIL','error':f'COM timed out after {a.timeout}s'}
            except Exception as exc:
                result={'status':'FAIL','error':repr(exc)}
            result.update({'filename':e['filename'],'source_sha256':e['sha256']})
            if output.is_file():result['word_saved_sha256']=hashlib.sha256(output.read_bytes()).hexdigest()
            results.append(result)
            print('NATIVE',result['status'],e['filename'],flush=True)
    summary={'created_at':datetime.now(timezone.utc).isoformat(),
             'generate_total':len(entries),'generate_pass':sum(e['status']=='PASS' for e in entries),
             'native_total':len(results),'native_pass':sum(e['status']=='PASS' for e in results),
             'native_fail':sum(e['status']!='PASS' for e in results),
             'word_gui_visual_signoff':'NOT_TESTED', 'cases':results}
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    archive=a.out/'MERGE_GRID_NATIVE_QA_RESULTS.zip'
    with ZipFile(archive,'w',ZIP_DEFLATED) as z:
        for path in sorted(a.out.rglob('*')):
            if path.is_file() and path!=archive:
                z.write(path,path.relative_to(a.out))
    print('RESULTS_ARCHIVE',archive,flush=True)
    return int(summary['generate_pass']!=summary['generate_total'] or (not a.generate_only and summary['native_fail']>0))

if __name__=='__main__':
    raise SystemExit(main())
