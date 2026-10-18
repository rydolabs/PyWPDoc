"""Execute PyWPDoc quality checks locally, without Git operations.

Usage: python scripts/run_local_qa.py
Runs full grouped regression, public test selector, and source compilation.
Exit status is nonzero on any failed check. Never accesses Git or publishes.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / '.test-results'

CHECKS = (
    ('grouped-regression', (sys.executable, 'scripts/run_ci_regression_groups.py')),
    ('public-selector', (sys.executable, 'scripts/run_public_tests.py')),
    ('compile-source', (sys.executable, '-m', 'compileall', '-q', 'src/pywpdoc')),
)

def main() -> int:
    RESULTS.mkdir(exist_ok=True)
    checks = []
    for label, command in CHECKS:
        print(f'[LOCAL QA] {label}', flush=True)
        try:
            outcome = subprocess.run(command, cwd=ROOT, check=False)
            code = outcome.returncode
        except OSError as exc:
            print(f'[LOCAL QA] cannot start {label}: {exc}', file=sys.stderr, flush=True)
            code = 127
        checks.append({'name': label, 'exit_code': code, 'passed': code == 0})
        if code != 0:
            print(f'[LOCAL QA FAIL] {label}: exit code {code}', flush=True)
            break
    all_pass = len(checks) == len(CHECKS) and all(item['passed'] for item in checks)
    summary = {'created_utc': datetime.now(timezone.utc).isoformat(),
               'all_pass': all_pass, 'checks': checks,
               'scope': 'LOCAL TEST ONLY - no repository manipulation or publishing'}
    (RESULTS / 'local_qa_summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print('[LOCAL QA PASS] All checks passed. No files uploaded.' if all_pass
          else '[LOCAL QA FAIL] See .test-results for logs. No files uploaded.', flush=True)
    return 0 if all_pass else 1

if __name__ == '__main__':
    raise SystemExit(main())
