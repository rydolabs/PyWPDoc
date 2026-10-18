"""Isolated COM process per merged-grid case (Windows only)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import traceback
from tests.generators.business_docs.merge_grid import CASES_BY_KEY, check_common_api, assert_word_merge_semantics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pdf', type=Path, required=True)
    a = parser.parse_args()
    case = CASES_BY_KEY.get(a.source.stem)
    fmt = a.source.suffix.lower().lstrip('.')
    result = {'id':a.source.stem,'format':fmt,'native_save':'NOT_TESTED',
              'semantic':'NOT_TESTED','pdf':'NOT_TESTED','status':'FAIL'}
    if case is None or fmt not in ('docx','hwpx'):
        result['error'] = 'unknown merge-grid case or format'
        print(json.dumps(result,ensure_ascii=False),flush=True)
        return 2
    import pythoncom
    import win32com.client
    app = None
    opened = None
    pythoncom.CoInitialize()
    try:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.pdf.parent.mkdir(parents=True,exist_ok=True)
        if fmt == 'docx':
            app = win32com.client.DispatchEx('Word.Application')
            app.Visible = False
            app.DisplayAlerts = 0
            opened = app.Documents.Open(str(a.source.resolve()),ReadOnly=True,AddToRecentFiles=False)
            opened.SaveAs2(str(a.output.resolve()),FileFormat=16)
            result['native_save'] = 'PASS'
            try:
                opened.ExportAsFixedFormat(str(a.pdf.resolve()),ExportFormat=17)
                result['pdf'] = 'PASS' if a.pdf.is_file() and a.pdf.stat().st_size > 200 else 'FAIL'
            except Exception as err:
                result['pdf'] = 'NOT_TESTED'
                result['pdf_error'] = repr(err)
        else:
            app = win32com.client.DispatchEx('HWPFrame.HwpObject')
            try:
                app.XHwpWindows.Item(0).Visible = True
            except Exception: pass
            ok = app.Open(str(a.source.resolve()), 'HWPX', '')
            if ok is False: raise RuntimeError('Hancom Open returned False')
            app.SaveAs(str(a.output.resolve()), 'HWPX', '')
            result['native_save'] = 'PASS'
            try:
                app.SaveAs(str(a.pdf.resolve()), 'PDF', '')
                result['pdf'] = 'PASS' if a.pdf.is_file() and a.pdf.stat().st_size > 200 else 'NOT_TESTED'
            except Exception as err:
                result['pdf_error'] = repr(err)
        if not a.output.is_file() or a.output.stat().st_size < 200:
            raise AssertionError('Native editor did not produce a saved document')
        result['common_api'] = check_common_api(a.output,case)
        if fmt == 'docx':
            result['word_semantics'] = assert_word_merge_semantics(a.source,a.output)
        result['semantic'] = 'PASS'
        result['status'] = 'PASS'
        return 0
    except Exception:
        result['status']='FAIL'
        result['error']=traceback.format_exc()
        return 2
    finally:
        if opened is not None:
            try: opened.Close(SaveChanges=False)
            except Exception: pass
        if app is not None:
            try:
                if fmt == 'hwpx': app.Clear(1)
                app.Quit()
            except Exception: pass
        pythoncom.CoUninitialize()
        print(json.dumps(result,ensure_ascii=False),flush=True)

if __name__=='__main__':
    raise SystemExit(main())
