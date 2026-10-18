# -*- coding: utf-8 -*-
"""Isolated COM worker: a hung Office instance is terminated by its parent timeout.

Never edits originals. Return value from HWP COM is not sufficient as oracle;
verified output must be re-opened and semantically compared.
"""
from __future__ import annotations
import argparse, json, sys, traceback
from pathlib import Path
from docx import Document as NativeDocument
from pywpdoc import Document
from extended_document_qa import structure,package_check


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--app',choices=['hwp','word'],required=True)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--dest',type=Path,required=True)
    args=parser.parse_args()
    import win32com.client
    app=None;opened=None
    try:
        if args.app=='hwp':
            try: app=win32com.client.DispatchEx('HWPFrame.HwpObject')
            except Exception as ex:
                print(json.dumps({'status':'SKIP','reason':'Hangul COM unavailable: '+repr(ex)},ensure_ascii=False),flush=True)
                return 4
            try:app.XHwpWindows.Item(0).Visible=True
            except Exception:pass
            if app.Open(str(args.source.resolve()),'HWPX','') is False:raise RuntimeError('HWP Open returned False')
            ret=app.SaveAs(str(args.dest.resolve()),'HWPX','')
            # SaveAs return False does not prove failure. Check file instead.
        else:
            try: app=win32com.client.DispatchEx('Word.Application')
            except Exception as ex:
                print(json.dumps({'status':'SKIP','reason':'Word COM unavailable: '+repr(ex)},ensure_ascii=False),flush=True)
                return 4
            app.Visible=False;app.DisplayAlerts=0
            opened=app.Documents.Open(str(args.source.resolve()))
            opened.SaveAs2(str(args.dest.resolve()),FileFormat=16)
            opened.Close(False);opened=None
            ret='SavedAs2'
        if not args.dest.is_file() or args.dest.stat().st_size<200:
            raise RuntimeError(f'COM did not create output (return={ret!r})')
        package_check(args.dest)
        before=structure(Document.open(args.source))
        after=structure(Document.open(args.dest))
        keys=('paragraphs','grids','nested_text','image_count','title','author','bold_snippets')
        checks={k:before[k]==after[k] for k in keys}
        result={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'action_return':repr(ret)}
        print(json.dumps(result,ensure_ascii=False),flush=True)
        return 0 if result['status']=='PASS' else 2
    except Exception:
        print(json.dumps({'status':'ERROR','traceback':traceback.format_exc()},ensure_ascii=False),flush=True)
        return 3
    finally:
        if opened is not None:
            try:opened.Close(False)
            except Exception:pass
        if app is not None:
            try:
                if args.app=='hwp':app.Clear(1)
                app.Quit()
            except Exception:pass

if __name__=='__main__':raise SystemExit(main())
