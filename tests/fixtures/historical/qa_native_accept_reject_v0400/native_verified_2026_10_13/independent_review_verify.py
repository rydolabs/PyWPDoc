import json, zipfile, io, hashlib
from lxml import etree
from pathlib import Path
OUTER=Path(__file__).resolve().parent / 'HWP_REVIEW_RESULTS_V2_NATIVE.zip'

def local(el):return etree.QName(el).localname

def decode(data):
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  assert z.testzip() is None
  hdr=etree.fromstring(z.read('Contents/header.xml'))
  sec=etree.fromstring(z.read('Contents/section0.xml'))
  charprops={e.get('id'):any(local(c)=='bold' for c in e) for e in hdr.iter() if local(e)=='charPr'}
  parprops={e.get('id'):next((c.get('horizontal') for c in e if local(c)=='align'),None) for e in hdr.iter() if local(e)=='paraPr'}
  markers=sum(local(e) in ('insertBegin','insertEnd','deleteBegin','deleteEnd') for e in sec.iter())
  anchors=[(local(e),k,v) for e in sec.iter() for k,v in e.attrib.items() if etree.QName(k).localname in ('charTcId','paraTcId')]
  recs=[e for e in hdr.iter() if local(e)=='trackChange']
  tables={}
  for tbl in (e for e in sec.iter() if local(e)=='tbl'):
   tr=[x for x in tbl if local(x)=='tr']
   if not tr: continue
   cells=[[x for x in row if local(x)=='tc'] for row in tr]
   def text(c):
    # direct hp:t nodes including revisions; ignore annotations
    return '\n'.join(''.join(t.itertext()) for para in c.iter() if local(para)=='p' for run in para if local(run)=='run' for t in run if local(t)=='t')
   rows=[[text(c) for c in r] for r in cells]
   key=rows[0][0] if rows and rows[0] else ''
   if key[:1] not in ('S','T'): continue
   spans=[]
   for r in cells:
    spans.append([next(((int(e.get('colSpan','1')),int(e.get('rowSpan','1'))) for e in c if local(e)=='cellSpan'),(1,1)) for c in r])
   vals=[]
   for c in cells[1][1:2]:
    for p in (x for x in c.iter() if local(x)=='p'):
     vals.append({'align':parprops.get(p.get('paraPrIDRef')),
                  'runbold':[charprops.get(run.get('charPrIDRef')) for run in p if local(run)=='run' and any(local(t)=='t' and ''.join(t.itertext()) for t in run)]})
   tables[key]={'rows':rows,'spans':spans,'cols':int(tbl.get('colCnt',0)), 'cell_styles':vals}
  return {'sha256':hashlib.sha256(data).hexdigest(),'markers':markers,'anchors':anchors,'header_revisions':len(recs),'tables':tables}

with zipfile.ZipFile(OUTER) as z:
 raw={name:z.read(name) for name in ('INPUT_ACCEPT_COPY.hwpx','INPUT_REJECT_COPY.hwpx','ACCEPT_ALL_NATIVE.hwpx','REJECT_ALL_NATIVE.hwpx')}
 ob={name:decode(content) for name,content in raw.items()}
 src=ob['INPUT_ACCEPT_COPY.hwpx']
 acc=ob['ACCEPT_ALL_NATIVE.hwpx']
 rej=ob['REJECT_ALL_NATIVE.hwpx']
 checks={
 'original_copies_identical':raw['INPUT_ACCEPT_COPY.hwpx']==raw['INPUT_REJECT_COPY.hwpx'],
 'original_markers_present':src['markers']>=8 and len(src['anchors'])>=2 and src['header_revisions']>=6,
 'accept_markers_resolved':acc['markers']==0 and not acc['anchors'],
 'reject_markers_resolved':rej['markers']==0 and not rej['anchors'],
 'tracked_header_revisions_removed':acc['header_revisions']==0 and rej['header_revisions']==0,
 '10_tables_preserved':len(src['tables'])==len(acc['tables'])==len(rej['tables'])==10 and src['tables'].keys()==acc['tables'].keys()==rej['tables'].keys(),
 }
 for mode,target,expected in (('accept',acc,{'T01_INSERT':'ABCD','T02_DELETE':'ABC','T03_REPLACE':'NEW'}), ('reject',rej,{'T01_INSERT':'ABC','T02_DELETE':'ABCD','T03_REPLACE':'OLD'})):
  for case,val in expected.items():checks[mode+'_'+case]=target['tables'][case]['rows'][1][1]==val
  bold=target['tables']['T04_CHAR']['cell_styles'][0]['runbold']
  align=target['tables']['T05_PARA']['cell_styles'][0]['align']
  checks[mode+'_bold']=bool(bold) and all(b is (mode=='accept') for b in bold)
  checks[mode+'_para']=align==('CENTER' if mode=='accept' else 'JUSTIFY')
  for case in ('S06_ROW_INSERT','S07_ROW_DELETE','S08_COL_INSERT','S09_COL_DELETE','S10_CELL_MERGE'):
   checks[mode+'_preserves_'+case]=all(target['tables'][case][f]==src['tables'][case][f] for f in ('rows','spans','cols'))
 result={'checks':checks,'total':len(checks),'passed':sum(checks.values()),'failed':[k for k,v in checks.items() if not v], 'input_source_sha256':src['sha256'],'accept_sha256':acc['sha256'],'reject_sha256':rej['sha256'], 'counts': {n: {k:v for k,v in d.items() if k!='tables'} for n,d in ob.items()}}
 out=Path(__file__).resolve().parent / 'independent_review_validation.json'
 out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Independent checks:',result['passed'],'/',result['total'],'fails:',result['failed'])
 print('input:',src['markers'],len(src['anchors']),src['header_revisions'])
 print('accept:',acc['markers'],len(acc['anchors']),acc['header_revisions'])
 print('reject:',rej['markers'],len(rej['anchors']),rej['header_revisions'])
