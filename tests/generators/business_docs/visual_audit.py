"""Conservative PDF-render checks; never substitutes for visual human signoff."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from tests.generators.business_docs.scenarios import SCENARIOS


def inspect_pdf(pdf_path: Path, *, preview_dir: Path | None = None) -> dict:
    import fitz
    document = fitz.open(pdf_path)
    full_text = '\n'.join(p.get_text() for p in document)
    scenario = next((s for s in SCENARIOS if s.key == pdf_path.stem), None)
    if scenario is None:
        raise ValueError(f'unknown scenario: {pdf_path.stem}')
    sentinel = f'QA-SCENARIO::{scenario.key}::docx::END'
    result = {'file':pdf_path.name, 'pages':len(document),
              'title_found':''.join(scenario.title.split()) in ''.join(full_text.split()),
              'end_sentinel_found':sentinel in full_text,
              'text_chars':len(full_text), 'empty_pages':[], 'outside_page_text':[]}
    for i,page in enumerate(document):
        if not page.get_text().strip():
            result['empty_pages'].append(i+1)
        # Detect text boxes beyond page boundaries, not subtle overlap/clipping.
        rect = page.rect
        bad = []
        for block in page.get_text('blocks'):
            if block[6] != 0:
                continue
            x0,y0,x1,y1=block[:4]
            if x0 < -2 or y0 < -2 or x1 > rect.width + 2 or y1 > rect.height + 2:
                bad.append((x0,y0,x1,y1))
        if bad:
            result['outside_page_text'].append({'page':i+1,'blocks':bad})
    result['status'] = ('PASS' if (result['title_found'] and result['end_sentinel_found']
                                  and not result['empty_pages'] and not result['outside_page_text']) else 'FAIL')
    if preview_dir is not None:
        from PIL import Image
        preview_dir.mkdir(parents=True, exist_ok=True)
        for idx in sorted(set([0,len(document)-1])):
            pix = document[idx].get_pixmap(matrix=fitz.Matrix(1.3,1.3), alpha=False)
            pix.save(str(preview_dir / f'{scenario.key}_page_{idx+1}.png'))
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--pdfdir',type=Path,required=True)
    p.add_argument('--out',type=Path,default=Path('business_qa_results/pdf_audit.json'))
    p.add_argument('--snapshots',type=Path)
    a=p.parse_args()
    rows=[]
    for s in SCENARIOS:
        f=a.pdfdir/(s.key+'.pdf')
        rows.append(inspect_pdf(f, preview_dir=a.snapshots) if f.exists() else
                    {'file':f.name,'status':'FAIL','error':'missing rendered PDF'})
    report={'total':len(rows),'pass':sum(r['status']=='PASS' for r in rows),
            'fail':sum(r['status']=='FAIL' for r in rows),
            'human_approval':'NOT_TESTED','cases':rows}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},ensure_ascii=False))
    return int(report['fail'] > 0)

if __name__=='__main__': raise SystemExit(main())
