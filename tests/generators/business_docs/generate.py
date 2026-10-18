"""Generate and audit 48 real files for Windows Word/Hancom compatibility review.

Run from the PyWPDoc project root:
 python -m qa_business_docs.generate --out path/to/generated
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import traceback
from tests.generators.business_docs.scenarios import SCENARIOS, build_document, open_and_check
from tests.generators.business_docs.audit import audit_archive


def generate(out: Path, *, formats: tuple[str, ...] = ('docx', 'hwpx'), only: set[str] | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    entries = []
    for s in SCENARIOS:
        if only is not None and s.key not in only:
            continue
        for fmt in formats:
            path = out / f'{s.key}.{fmt}'
            result = {'id': s.key, 'title': s.title, 'domain': s.domain, 'format': fmt,
                      'filename': path.name, 'flags': {'image': s.image, 'nested': s.nested,
                      'merged': s.merged, 'template': s.template, 'long': s.long}}
            try:
                doc, expected = build_document(s, fmt)
                doc.save(path)
                result['structure'] = open_and_check(path, expected)
                result['archive'] = audit_archive(path, expect_image=s.image)
                result['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
                result['status'] = 'PASS'
            except Exception as error:
                result['status'] = 'FAIL'
                result['error'] = repr(error)
                result['traceback'] = traceback.format_exc()
            entries.append(result)
            print(f"{result['status']} {path.name}", flush=True)
    report = {'product': 'PyWPDoc', 'candidate': __import__('importlib.metadata', fromlist=['version']).version('pywpdoc'),
              'generated_at': datetime.now(timezone.utc).isoformat(),
              'total': len(entries), 'passed': sum(x['status'] == 'PASS' for x in entries),
              'failed': sum(x['status'] != 'PASS' for x in entries), 'cases': entries,
              'native_word': 'NOT_TESTED', 'native_hancom': 'NOT_TESTED', 'visual_review': 'NOT_TESTED'}
    (out / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, default=Path('business_qa_results') / 'generated')
    p.add_argument('--format', choices=['both', 'docx', 'hwpx'], default='both')
    p.add_argument('--only', nargs='*', default=[])
    a = p.parse_args()
    formats = ('docx', 'hwpx') if a.format == 'both' else (a.format,)
    r = generate(a.out, formats=formats, only=set(a.only) if a.only else None)
    print(json.dumps({k:v for k,v in r.items() if k != 'cases'},ensure_ascii=False,indent=2))
    return int(r['failed'] != 0)


if __name__ == '__main__':
    raise SystemExit(main())
