"""Windows Word/Hancom supervisor: per-file timeout, all cases continue.

python -m qa_business_docs.windows_review --generated business_qa_results/generated
All failures and omissions are recorded. A COM save is *not* visual approval.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import zipfile


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--generated', type=Path, default=Path('business_qa_results/generated'))
    a.add_argument('--out', type=Path, default=Path('business_qa_results/native_windows'))
    a.add_argument('--timeout', type=int, default=240)
    a.add_argument('--only', nargs='*', default=[])
    args = a.parse_args()
    source_manifest = args.generated / 'manifest.json'
    if not source_manifest.is_file():
        raise SystemExit('Run python -m qa_business_docs.generate first')
    src = json.loads(source_manifest.read_text(encoding='utf-8'))
    args.out.mkdir(parents=True, exist_ok=True)
    all_results = []
    cases = [r for r in src['cases'] if r['status']=='PASS' and (not args.only or r['id'] in args.only)]
    if not cases:
        raise SystemExit('No generated PASS cases selected for Windows validation')
    if args.only and (set(args.only) - {r['id'] for r in cases}):
        raise SystemExit('Missing generated PASS scenarios: ' + ', '.join(sorted(set(args.only) - {r['id'] for r in cases})))
    for case in cases:
        input_file = args.generated / case['filename']
        output = args.out / 'resaved' / case['filename']
        pdf = args.out / 'rendered_pdf' / (case['id'] + '-' + case['format'] + '.pdf')
        cmd = [sys.executable, '-m', 'tests.generators.business_docs.windows_native_worker', '--source', str(input_file),
               '--out', str(output), '--pdf', str(pdf)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
            try:
                result = json.loads(proc.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                result = {'status': 'FAIL', 'error': 'no parseable JSON', 'stdout': proc.stdout[-4000:]}
            if proc.returncode != 0:
                result['status'] = 'FAIL'
            if proc.stderr:
                result['stderr'] = proc.stderr[-4000:]
        except subprocess.TimeoutExpired:
            result = {'status': 'FAIL', 'error': 'TIMEOUT', 'timeout_seconds': args.timeout}
        except Exception as error:
            result = {'status': 'FAIL', 'error': repr(error)}
        # Bind results to the exact generated input used in this same COM run.
        source_hash = hashlib.sha256(input_file.read_bytes()).hexdigest() if input_file.is_file() else None
        result.update({'case_id': case['id'], 'filename': case['filename'],
                       'source_sha256': source_hash,
                       'expected_source_sha256': case.get('sha256'),
                       'source_hash_verified': source_hash == case.get('sha256')})
        if source_hash != case.get('sha256'):
            result['status'] = 'FAIL'
            result['source_error'] = 'Input SHA256 differs from generated manifest'
        if output.is_file():
            result['resaved_sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
        all_results.append(result)
        print(f"{result.get('status')} {case['filename']} PDF={result.get('pdf_export','NOT_TESTED')}", flush=True)
        # Continue after each failure: no catastrophic batch abort.
    summary = {'created_at': datetime.now(timezone.utc).isoformat(),
               'source_manifest': str(source_manifest), 'total': len(all_results),
               'native_pass': sum(r['status']=='PASS' for r in all_results),
               'native_fail': sum(r['status']!='PASS' for r in all_results),
               'pdf_pass': sum(r.get('pdf_export')=='PASS' for r in all_results),
               'pdf_not_tested': sum(r.get('pdf_export')=='NOT_TESTED' for r in all_results),
               'visual_human_signoff': 'NOT_TESTED', 'cases': all_results}
    (args.out / 'windows_results.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    with (args.out/'VISUAL_REVIEW_CHECKLIST.csv').open('w',newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['case_id','format','Word/Hancom open-save','PDF export','page count verified','text clipped','tables visible','images placed correctly','manual signoff','remarks'])
        for r in all_results:
            writer.writerow([r['case_id'],Path(r['filename']).suffix.lstrip('.'),r.get('open_save','FAIL'),
                             r.get('pdf_export','NOT_TESTED'),'NOT_TESTED','NOT_TESTED','NOT_TESTED','NOT_TESTED','NOT_TESTED',''])
    archive = args.out / 'BUSINESS_NATIVE_QA_RESULTS.zip'
    with zipfile.ZipFile(archive,'w', compression=zipfile.ZIP_DEFLATED) as z:
        for p in args.out.rglob('*'):
            if p.is_file() and p != archive:
                z.write(p,p.relative_to(args.out))
        # Crucial audit evidence: the *actual* input files, not regenerated
        # approximations from a different run. Include only selected cases.
        z.write(source_manifest, 'generated_inputs/manifest.json')
        for case in cases:
            p = args.generated / case['filename']
            if p.is_file():
                z.write(p, 'generated_inputs/' + case['filename'])
    print('RESULTS_ARCHIVE',archive)
    return int(summary['native_fail'] > 0)


if __name__=='__main__':
    raise SystemExit(main())
