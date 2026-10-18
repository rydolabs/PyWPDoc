# -*- coding: utf-8 -*-
"""PyWPDoc release-candidate native integration smoke test.

Offline mode is intentional: all Windows application checks report SKIP, not
PASS. A native PASS requires a fresh COM session, saved document and semantic
inspection. Uses no visible user's document and always writes under results/.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys
import traceback
from zipfile import ZipFile, ZIP_DEFLATED

BASE = Path(__file__).resolve().parent
from verify_review_hwpx import inspect_hwpx, compare_review, preflight


def sh(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def members(path):
    with ZipFile(path) as z:
        assert z.testzip() is None, 'corrupt zip'
        return {n: hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}


def validate_package(path):
    from lxml import etree
    with ZipFile(path) as z:
        assert z.testzip() is None
        names = set(z.namelist())
        main = 'word/document.xml' if path.suffix == '.docx' else 'Contents/section0.xml'
        assert main in names
        for n in names:
            if n.endswith(('.xml', '.rels', '.hpf')):
                etree.fromstring(z.read(n), etree.XMLParser(recover=False, resolve_entities=False))


def save_check(doc, target):
    doc.save(target)
    validate_package(target)
    return target


def rt_hwp(session, source, target):
    """COM return False is never a success or failure oracle by itself."""
    session.Clear(1)
    ok = session.Open(str(source.resolve()), 'HWPX', '')
    if ok is False:
        raise RuntimeError('HWP Open returned False')
    if target.exists():
        target.unlink()
    ret = session.SaveAs(str(target.resolve()), 'HWPX', '')
    if not target.exists() or target.stat().st_size < 100:
        raise RuntimeError(f'HWP SaveAs produced no file (return={ret!r})')
    validate_package(target)
    return repr(ret)


def start_hwp():
    """Start Hancom with the user-approved official Automation access module.

    Never simulate clicks on a security prompt. If the module is unavailable,
    stop before opening any file and leave the user's Hancom security intact.
    """
    import winreg
    import win32com.client

    module_name = 'FilePathCheckerModuleExample'
    reg_path = r'Software\HNC\HwpAutomation\Modules'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
        dll_path, value_type = winreg.QueryValueEx(key, module_name)
    if value_type != winreg.REG_SZ or not isinstance(dll_path, str):
        raise RuntimeError('Hancom security module registry value must be REG_SZ')
    if not Path(dll_path).is_file():
        raise RuntimeError('Hancom official Automation module DLL not found: ' + dll_path)

    app = win32com.client.DispatchEx('HWPFrame.HwpObject')
    try:
        if app.RegisterModule('FilePathCheckDLL', module_name) is False:
            raise RuntimeError('Hancom security module registration failed: check official DLL and Hancom bitness')
        try:
            app.XHwpWindows.Item(0).Visible = True
        except Exception:
            pass
        return app
    except Exception:
        try:
            app.Quit()
        except Exception:
            pass
        raise


def start_word():
    import win32com.client
    app = win32com.client.DispatchEx('Word.Application')
    app.Visible = False
    app.DisplayAlerts = 0
    return app


def close_app(app):
    if app is None: return
    try:
        if hasattr(app, 'Clear'): app.Clear(1)
    except Exception: pass
    try: app.Quit()
    except Exception: pass


def test_h01(work, native):
    import base64
    from pywpdoc import Document, Mm
    d = Document.new('hwpx')
    d.add_paragraph('원본 보존 검증 A\tB\nC')
    t = d.add_table(2, 2)
    for r in range(2):
        for c in range(2): t.cell(r, c).text = f'표-{r}-{c}'
    png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
    d.add_picture(png, 'png', width=Mm(10), height=Mm(10))
    d.sections[0].left_margin=Mm(18)
    before = save_check(d, work/'H01_input.hwpx')
    loaded = Document.open(before)
    assert any('원본 보존' in p.text for p in loaded.paragraphs)
    assert len(loaded.tables) == 1
    assert len(loaded.pictures) == 1
    if not native: return 'SKIP', 'Python package checked; native HWP unavailable'
    app = None
    try:
        app = start_hwp()
        target = work/'H01_native_saved.hwpx'
        ret = rt_hwp(app, before, target)
        again = Document.open(target)
        assert any(p.text == '원본 보존 검증 A\tB\nC' for p in again.paragraphs)
        assert [[c.text for c in row.cells] for row in again.tables[0].rows] == [[c.text for c in row.cells] for row in loaded.tables[0].rows]
        assert len(again.pictures) == 1
        assert abs(again.sections[0].left_margin.mm-18)<0.15
        return 'PASS', f'HWPX native reopen/save; return={ret}'
    finally: close_app(app)


def test_h02(work, native):
    from pywpdoc import Document
    d = Document.new('hwpx')
    d.add_paragraph('이름 {{name}} / {{missing}}')
    before = save_check(d, work/'H02_before.hwpx')
    report = d.check_template({'name': '홍길동'})
    assert not report.ok
    assert len(report.issues) > 0
    after = save_check(d, work/'H02_after.hwpx')
    assert members(before) == members(after)
    return 'PASS', 'missing variable detected; no mutation'


def test_h03(work, native):
    from pywpdoc import Document
    d = Document.new('hwpx')
    d.add_paragraph('고객 {{customer}}')
    t = d.add_table(2, 2)
    t.cell(0, 0).text = '항목'
    t.cell(0, 1).text = '번호'
    t.cell(1, 0).text = '{{#items}}{{name}}'
    t.cell(1, 1).text = '{{code}}{{/items}}'
    data = {'customer':'홍길동', 'items':[{'name':'가','code':'AA'},{'name':'나','code':'BB'}]}
    assert d.check_template(data, sections=True, table_rows=True).ok
    assert d.render_template(data, sections=True, table_rows=True) > 0
    p = save_check(d, work/'H03_rendered.hwpx')
    assert [r.cells[1].text for r in Document.open(p).tables[0].rows] == ['번호','AA','BB']
    if not native: return 'SKIP', 'Rendered HWPX passed; native HWP unavailable'
    app = None
    try:
        app = start_hwp(); out = work/'H03_native_saved.hwpx'
        rt_hwp(app, p, out)
        got = Document.open(out)
        assert any('홍길동' in para.text for para in got.paragraphs)
        assert [r.cells[1].text for r in got.tables[0].rows] == ['번호','AA','BB']
        return 'PASS', 'HWP native template table repeat retained'
    finally: close_app(app)


def test_h04(work, native):
    from pywpdoc import Document
    d = Document.new('hwpx')
    d.add_paragraph('AA AA')
    b = save_check(d, work/'H04_before.hwpx')
    report = d.preview_replace('AA','BB')
    assert report.count == 2
    assert json.loads(report.to_json())['count'] == 2
    a = save_check(d, work/'H04_after_preview.hwpx')
    assert members(b) == members(a)
    assert d.replace_text('AA','BB') == 2
    result = save_check(d, work/'H04_replaced.hwpx')
    assert 'BB BB' in Document.open(result).paragraphs[-1].text
    return 'PASS', 'preview/actual count match and preview immutable'


def test_h05(work, native):
    from pywpdoc import Document
    d = Document.new('hwpx')
    p = d.add_paragraph()
    p.add_run('2026-')
    p.add_run('10-14')
    assert len(d.find_regex(r'\d{4}-\d{2}-\d{2}')) == 1
    assert d.replace_regex(r'(\d{4})-(\d{2})-(\d{2})', r'\1.\2.\3') == 1
    source = save_check(d, work/'H05_regex.hwpx')
    assert any('2026.10.14' in p.text for p in Document.open(source).paragraphs)
    if not native: return 'SKIP', 'Regex transformed HWPX saved; native HWP unavailable'
    app = None
    try:
        app=start_hwp(); out=work/'H05_native_saved.hwpx'
        rt_hwp(app, source, out)
        assert any('2026.10.14' in p.text for p in Document.open(out).paragraphs)
        return 'PASS', 'HWP native regex output survived roundtrip'
    finally: close_app(app)


def test_h06(work, native):
    from pywpdoc import Document, DocumentValueError, DocumentUnsupportedError
    d = Document.new('hwpx'); d.add_paragraph('A1 B2 C3')
    b = save_check(d, work/'H06_before.hwpx')
    try: d.replace_regex('[', 'X')
    except DocumentValueError: pass
    else: raise AssertionError('invalid regex incorrectly accepted')
    try: d.replace_regex(r'(?=B2)|[A-Z]\d', 'X')
    except DocumentUnsupportedError: pass
    else: raise AssertionError('zero-width match incorrectly accepted')
    a = save_check(d, work/'H06_after.hwpx')
    assert members(b) == members(a)
    return 'PASS', 'invalid/zero-width regex atomically blocked'


def test_h07(work, native):
    from pywpdoc import Document
    orig = BASE/'SOURCE_TRACKED_V22.hwpx'
    base = BASE/'BASE_BEFORE_EDIT.hwpx'
    pf = preflight(orig, base)
    assert pf['status'] == 'PASS', pf
    # Read-only APIs on native tracked document must not disrupt markers.
    baseline = work/'H07_baseline.hwpx'
    Document.open(orig).save(baseline)
    d = Document.open(orig)
    assert d.check_template({}).ok
    assert len(d.find_regex(r'[A-Z]{2,4}')) > 0
    assert d.preview_replace('NEW', 'UPD').count >= 1
    preserved = work/'H07_preflight_saved.hwpx'
    save_check(d, preserved)
    assert members(baseline) == members(preserved)
    if not native: return 'SKIP', 'Prior native fixture unchanged; accept/reject COM unavailable'
    original_state = inspect_hwpx(preserved)
    checks = []
    for mode, action in (('accept','TrackChangeApplyAll'),('reject','TrackChangeCancelAll')):
        app = None
        try:
            inp = work/f'H07_{mode}_input.hwpx'; shutil.copy2(preserved, inp)
            app = start_hwp()
            app.Clear(1)
            if app.Open(str(inp.resolve()), 'HWPX', '') is False:
                raise RuntimeError('HWP Open False: '+mode)
            action_return = app.HAction.Run(action)
            output = work/f'H07_{mode}_native.hwpx'
            if output.exists(): output.unlink()
            saved_return = app.SaveAs(str(output.resolve()), 'HWPX','')
            if not output.exists(): raise RuntimeError(f'No {mode} saved result')
            validate_package(output)
            review = compare_review(original_state, inspect_hwpx(output), mode)
            (work/f'H07_{mode}_review.json').write_text(json.dumps(review, ensure_ascii=False, indent=2),encoding='utf-8')
            checks.append((mode,review['status'],repr(action_return),repr(saved_return)))
        finally: close_app(app)
    assert all(row[1]=='PASS' for row in checks), checks
    return 'PASS', f'Native accept+reject semantic inspection: {checks}'


def test_h08(work, native):
    from pywpdoc import Document, DocumentUnsupportedError
    a,b=Document.new('hwpx'),Document.new('hwpx')
    a.add_table(1,1).cell(0,0).text='A'
    b.add_table(2,1).cell(0,0).text='A'
    a_path=save_check(a,work/'H08_a.hwpx');b_path=save_check(b,work/'H08_b.hwpx')
    ha,hb=members(a_path),members(b_path)
    try: a.compare(b)
    except DocumentUnsupportedError: pass
    else: raise AssertionError('unsafe row tracking unexpectedly enabled')
    assert a.preview_replace('A','B').count==1
    assert members(a_path)==ha and members(b_path)==hb
    return 'PASS', 'unsupported HWPX table row tracking fail-closed'


def test_w01(work, native):
    from pywpdoc import Document
    d=Document.new('docx'); d.add_paragraph('Word compatible 문서')
    tbl=d.add_table(1,2);tbl.cell(0,0).text='A';tbl.cell(0,1).text='B'
    inp=save_check(d,work/'W01_common.docx')
    if not native: return 'SKIP','Word COM unavailable in offline mode'
    app=None;opened=None
    try:
        try: app=start_word()
        except Exception as ex: return 'SKIP', 'Microsoft Word COM not available: '+repr(ex)
        opened=app.Documents.Open(str(inp.resolve()))
        out=work/'W01_word_saved.docx'
        opened.SaveAs2(str(out.resolve()),FileFormat=16)
        opened.Close(False);opened=None
        validate_package(out)
        d2=Document.open(out)
        assert any('Word compatible' in p.text for p in d2.paragraphs)
        assert [c.text for c in d2.tables[0].rows[0].cells]==['A','B']
        return 'PASS','Word COM open/save and semantic structure retained'
    finally:
        if opened is not None:
            try: opened.Close(False)
            except Exception: pass
        close_app(app)


def test_w02(work,native):
    from pywpdoc import Document
    old,new=Document.new('docx'),Document.new('docx')
    old.add_paragraph('OLD word text')
    new.add_paragraph('NEW word text')
    tracked=old.compare(new,author='RC',date='2026-10-14T00:00:00Z')
    inp=save_check(tracked,work/'W02_tracked.docx')
    with ZipFile(inp) as z: assert b'<w:ins' in z.read('word/document.xml')
    if not native: return 'SKIP','Word COM unavailable in offline mode'
    app=None
    try:
        try: app=start_word()
        except Exception as ex: return 'SKIP', 'Microsoft Word COM not available: '+repr(ex)
        for mode in ('accept','reject'):
            word_doc=app.Documents.Open(str(inp.resolve()))
            try:
                if mode=='accept':word_doc.Revisions.AcceptAll()
                else:word_doc.Revisions.RejectAll()
                output=work/f'W02_{mode}.docx'
                word_doc.SaveAs2(str(output.resolve()),FileFormat=16)
            finally:word_doc.Close(False)
            validate_package(output)
            with ZipFile(output) as pkg:
                main_xml=pkg.read('word/document.xml')
                assert b'<w:ins' not in main_xml and b'<w:del' not in main_xml, 'Unresolved Word revisions'
            result=Document.open(output)
            body=' '.join(p.text for p in result.paragraphs)
            assert ('NEW word text' if mode=='accept' else 'OLD word text') in body,(mode,body)
        return 'PASS','Word native AcceptAll/RejectAll semantics correct'
    finally: close_app(app)

def test_c01(work, native):
    import subprocess
    result=subprocess.run(
        [sys.executable, '-m', 'pytest', '-q', str(BASE/'test_release_python_docx_port_v0430.py')],
        cwd=str(BASE), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180,
    )
    (work/'pytest_output.txt').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    if result.returncode != 0:
        raise AssertionError('Common API port suite failed, see pytest_output.txt (exit '+str(result.returncode)+')')
    if '23 passed' not in result.stdout:
        raise AssertionError('Expected 23 selected port tests; inspect pytest_output.txt')
    return 'PASS','23 upstream-inspired Common API tests pass'


CASES={
 'H01':test_h01,'H02':test_h02,'H03':test_h03,'H04':test_h04,
 'H05':test_h05,'H06':test_h06,'H07':test_h07,'H08':test_h08,
 'W01':test_w01,'W02':test_w02,'C01':test_c01,
}


def bundle(out):
    path=out.parent/(out.name+'.zip')
    with ZipFile(path,'w',ZIP_DEFLATED) as z:
        for p in sorted(out.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(out))
    return path


def run(output_dir,native):
    import pywpdoc
    output_dir.mkdir(parents=True,exist_ok=True)
    from importlib.metadata import version as installed_version
    assert pywpdoc.__version__ == installed_version('pywpdoc'), 'PyWPDoc module/distribution version mismatch' 
    records=[]
    for case,fn in CASES.items():
        folder=output_dir/case;folder.mkdir(exist_ok=True)
        row={'case':case,'status':'ERROR','details':''}
        try:
            row['status'],row['details']=fn(folder,native)
        except Exception as ex:
            row['details']=repr(ex)
            row['traceback']=traceback.format_exc()
            (folder/'error.txt').write_text(row['traceback'],encoding='utf-8')
        records.append(row)
        print(case,row['status'],row['details'],flush=True)
    summary={s:sum(r['status']==s for r in records) for s in ('PASS','FAIL','ERROR','SKIP')}
    report={'product_version':pywpdoc.__version__,'environment':'Windows COM' if native else 'offline (no COM)',
            'summary':summary,'records':records,'native_all_pass':native and all(r['status']=='PASS' for r in records),
            'important':'Offline SKIP is not PASS; no GUI or native Word/Hancom success may be inferred.'}
    (output_dir/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    with (output_dir/'results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['case','status','details']);w.writeheader()
        for r in records:w.writerow({k:r.get(k,'') for k in ('case','status','details')})
    (output_dir/'summary.md').write_text(f'# PyWPDoc v{pywpdoc.__version__} RC native QA\n\n'+
         '\n'.join(f"- {r['case']}: **{r['status']}** — {r['details']}" for r in records)+
         '\n\nNative All PASS: '+str(report['native_all_pass'])+'\n',encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--offline',action='store_true')
    p.add_argument('--output-dir',type=Path,default=BASE/'HWP_RC_RESULTS')
    args=p.parse_args()
    try:
        report=run(args.output_dir,args.offline is False)
    except Exception:
        args.output_dir.mkdir(parents=True,exist_ok=True)
        (args.output_dir/'fatal_error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        print('FATAL:',traceback.format_exc(),file=sys.stderr)
        return 3
    artifact=bundle(args.output_dir)
    print('RESULT_ZIP:',artifact,flush=True)
    return 0 if report['native_all_pass'] or args.offline and report['summary']['ERROR']==0 else 2

if __name__=='__main__':sys.exit(main())
