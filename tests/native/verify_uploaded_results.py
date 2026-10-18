"""Independent semantic recheck of user-supplied Windows long/stress artifacts."""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
from collections import Counter
from lxml import etree
from pywpdoc import Document
from extended_document_qa import structure
import json, sys

src=Path(sys.argv[1]);dest=Path(sys.argv[2]); dest.mkdir(parents=True,exist_ok=True)
results=[]
with ZipFile(src) as outer:
    assert outer.testzip() is None
    for profile in ('long','stress'):
        for app,fmt in (('word','docx'),('hwp','hwpx')):
            names=[f'extended/documents/{profile}_{fmt}.{fmt}', f'extended/documents/{profile}_{app}_native_saved.{fmt}']
            paths=[]
            for name in names:
                b=outer.read(name);path=dest/Path(name).name;path.write_bytes(b)
                with ZipFile(path) as inner:
                    assert inner.testzip() is None
                    for info in inner.infolist():
                        if info.filename.lower().endswith(('.xml','.rels','.hpf')):
                            etree.fromstring(inner.read(info.filename), parser=etree.XMLParser(resolve_entities=False,no_network=True))
                paths.append(path)
            a=structure(Document.open(paths[0]))
            b=structure(Document.open(paths[1]))
            keys=('paragraphs','grids','nested_text','image_count','title','author','bold_snippets')
            checks={k:a[k]==b[k] for k in keys}
            extra={}
            if fmt=='docx':
                with ZipFile(paths[0]) as z1,ZipFile(paths[1]) as z2:
                    imgs1=Counter(sha256(z1.read(n)).hexdigest() for n in z1.namelist() if n.startswith('word/media/'))
                    imgs2=Counter(sha256(z2.read(n)).hexdigest() for n in z2.namelist() if n.startswith('word/media/'))
                extra['media_byte_hash_match']=imgs1==imgs2
                extra['media_sha_before']=dict(imgs1)
                extra['media_sha_after']=dict(imgs2)
            results.append({'profile':profile,'application':app,'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'bold_region_count_before':len(a['bold_snippets']),'bold_region_count_after':len(b['bold_snippets']),**extra})
            print(profile,app,checks,'media',extra.get('media_byte_hash_match','N/A'),flush=True)
(dest/'independent_audit.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
