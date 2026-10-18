# -*- coding: utf-8 -*-
"""Standalone extended python-docx port + long-document/native QA runner."""
from __future__ import annotations
import argparse, csv, json, os
from pathlib import Path
import subprocess, sys, time

ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--offline',action='store_true')
    p.add_argument('--output-dir',type=Path,default=ROOT/'HWP_RC_RESULTS'/'extended')
    args=p.parse_args(); dest=args.output_dir;dest.mkdir(parents=True,exist_ok=True)
    results=[]
    def run(label,command,timeout):
        started=time.monotonic()
        try:
            cp=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
            (dest/f'{label}.log').write_text(cp.stdout+'\nSTDERR:\n'+cp.stderr,encoding='utf-8')
            status='PASS' if cp.returncode==0 else ('SKIP' if cp.returncode==4 else 'FAIL')
            note=f'exit={cp.returncode}; elapsed={time.monotonic()-started:.2f}s'
        except subprocess.TimeoutExpired as ex:
            text=lambda v: (v or b'').decode('utf-8',errors='replace') if isinstance(v,bytes) else (v or '')
            (dest/f'{label}.log').write_text(text(ex.stdout)+'\nSTDERR:\n'+text(ex.stderr)+'\nTIMEOUT',encoding='utf-8')
            status='TIMEOUT';note=f'limit={timeout}s'
        except Exception as ex:
            status='ERROR';note=repr(ex)
        entry={'id':label,'status':status,'note':note}
        results.append(entry);print('[EXTENDED]',entry,flush=True)
        return entry
    run('X01_python_docx_extended_port',
        [sys.executable,'-m','pytest','-q',str(ROOT/'test_python_docx_extended_port_v0430.py')],90)
    run('X04_bold_run_normalization_regression',
        [sys.executable,'-m','pytest','-q',str(ROOT/'test_bold_run_normalization_v0430.py')],90)
    result=run('X02_generate_compare_long_and_stress',
        [sys.executable,str(ROOT/'extended_document_qa.py'),'--profile','both','--output-dir',str(dest/'documents')],200)
    docs=dest/'documents'
    native=(os.name=='nt' and not args.offline)
    for profile in ('long','stress'):
        for app,source_format in [('word','docx'),('hwp','hwpx')]:
            label=f'X03_{profile}_{app}_roundtrip'
            source=docs/f'{profile}_{source_format}.{source_format}'
            output=docs/f'{profile}_{app}_native_saved.{source_format}'
            if not source.is_file() or result['status']!='PASS':
                entry={'id':label,'status':'SKIP','note':'source generation failed'}
                results.append(entry)
            elif not native:
                entry={'id':label,'status':'SKIP','note':'Windows COM not run; this is not a PASS'}
                results.append(entry)
            else:
                run(label,[sys.executable,str(ROOT/'native_long_roundtrip_worker.py'),
                           '--app',app,'--source',str(source),'--dest',str(output)],360)
    with (dest/'results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['id','status','note']);w.writeheader();w.writerows(results)
    (dest/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    counts={s:sum(x['status']==s for x in results) for s in ('PASS','FAIL','ERROR','TIMEOUT','SKIP')}
    (dest/'summary.md').write_text('# Extended python-docx & long-document QA\n\n'+
        '\n'.join(f'- {k}: {v}' for k,v in counts.items())+'\n\n'
        +('\n'.join(f"- {x['id']}: {x['status']} — {x['note']}" for x in results))+'\n',encoding='utf-8')
    print('SUMMARY',counts,flush=True)
    return 1 if counts['FAIL'] or counts['ERROR'] or counts['TIMEOUT'] else 0
if __name__=='__main__':raise SystemExit(main())
