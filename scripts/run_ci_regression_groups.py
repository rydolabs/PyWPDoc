"""Run all redistributable pytest suites in isolated, bounded processes.

No tests are dropped: partitioning prevents leaked global state from one
legacy module from causing intermittent cross-module slowdowns. Every group
runs even if a preceding group fails; overall exit status is nonzero unless
all groups succeed. The normal pytest suite remains available directly.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
import signal
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
from run_public_tests import EXCLUDED_FILES, EXCLUDED_CASES


def test_groups():
    plain = sorted(p for p in (ROOT / 'tests').glob('test_*.py')
                   if p.relative_to(ROOT).as_posix() not in EXCLUDED_FILES)
    assert len(plain) > 30, 'unexpectedly small test suite'
    return [
        ('common-business-packaging', [ROOT/'tests/common_api', ROOT/'tests/business_docs', ROOT/'tests/packaging']),
        ('legacy-01', plain[:20]),
        ('legacy-02', plain[20:40]),
        ('legacy-03', plain[40:]),
    ]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=ROOT/'.test-results'/'ci_regression_groups.json')
    ap.add_argument('--timeout',type=int,default=180)
    args=ap.parse_args()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    data=[]
    for label, paths in test_groups():
        junit=args.out.parent/(label+'.xml')
        command=[sys.executable,'-m','pytest','-q','--disable-warnings',
                 '-m','not native and not performance',
                 *['--deselect='+c for c in EXCLUDED_CASES],
                 f'--junitxml={junit}',*[str(p.relative_to(ROOT)) for p in paths]]
        print(f'[REGRESSION] {label} ({len(paths)} test paths)',flush=True)
        log_file = args.out.parent / (label + '.log')
        with log_file.open('w', encoding='utf-8') as output:
            popen_kwargs = {'cwd': ROOT, 'stdout': output, 'stderr': subprocess.STDOUT}
            if os.name == 'nt':
                popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                popen_kwargs['start_new_session'] = True
            proc = subprocess.Popen(command, **popen_kwargs)
            try:
                returncode = proc.wait(timeout=args.timeout)
                status = 'PASS' if returncode == 0 else 'FAIL'
                row = {'label': label, 'status': status, 'returncode': returncode,
                       'test_paths': len(paths), 'junit': str(junit), 'log_file': str(log_file)}
            except subprocess.TimeoutExpired:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                                   capture_output=True, timeout=15, check=False)
                else:
                    try: os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: proc.kill()
                row = {'label': label, 'status': 'TIMEOUT',
                       'timeout_seconds': args.timeout, 'log_file': str(log_file)}
        lines = log_file.read_text(encoding='utf-8', errors='replace').strip().splitlines()
        row['last_lines'] = lines[-5:]
        print(f"[{row['status']}] {label}: {row['last_lines'][-1] if row['last_lines'] else ''}",flush=True)
        data.append(row)
    report={'created_at':datetime.now(timezone.utc).isoformat(), 'groups':data,
            'all_pass':all(row['status']=='PASS' for row in data)}
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if report['all_pass'] else 1

if __name__=='__main__':raise SystemExit(main())
