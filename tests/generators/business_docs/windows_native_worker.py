"""One-file isolated Word/Hancom COM worker; Windows only.

The source document is never overwritten. A separate supervisor applies a
per-document timeout and records failures independently. PDF export is a
separate check: an editor may support open/save without PDF export.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import traceback
from tests.generators.business_docs.scenarios import SCENARIOS, open_and_check, build_document
from tests.generators.business_docs.audit import audit_archive


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--pdf', type=Path, required=True)
    a = ap.parse_args()
    fmt = a.source.suffix.lower().lstrip('.')
    scenario = next((s for s in SCENARIOS if a.source.stem == s.key), None)
    if scenario is None or fmt not in ('docx','hwpx'):
        print(json.dumps({'status': 'FAIL', 'error': 'unknown business scenario / format'}))
        return 2
    from pythoncom import CoInitialize, CoUninitialize
    import win32com.client
    app = None
    opened = None
    result = {'source': a.source.name, 'format': fmt, 'editor': 'Word' if fmt=='docx' else 'Hancom',
              'open_save': 'NOT_TESTED', 'semantic': 'NOT_TESTED', 'pdf_export': 'NOT_TESTED'}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.pdf.parent.mkdir(parents=True, exist_ok=True)
    CoInitialize()
    try:
        if fmt == 'docx':
            app = win32com.client.DispatchEx('Word.Application')
            app.Visible = False
            app.DisplayAlerts = 0
            opened = app.Documents.Open(str(a.source.resolve()), ReadOnly=True, AddToRecentFiles=False)
            opened.SaveAs2(str(a.out.resolve()), FileFormat=16)
            result['open_save'] = 'PASS'
            try:
                opened.ExportAsFixedFormat(str(a.pdf.resolve()), ExportFormat=17)
                result['pdf_export'] = 'PASS' if a.pdf.exists() and a.pdf.stat().st_size > 200 else 'FAIL'
            except Exception as err:
                result['pdf_export'] = 'NOT_TESTED'
                result['pdf_error'] = repr(err)
        else:
            app = win32com.client.DispatchEx('HWPFrame.HwpObject')
            # Hancom's supported Automation file-access security module must
            # be configured by the user once. Do not click or suppress security
            # dialogs; abort before Open if the module is not available.
            import winreg
            reg_path = r'Software\HNC\HwpAutomation\Modules'
            module_name = 'FilePathCheckerModuleExample'
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as reg_key:
                    dll_path, reg_type = winreg.QueryValueEx(reg_key, module_name)
                if reg_type != winreg.REG_SZ or not isinstance(dll_path, str):
                    raise RuntimeError('Security DLL registry entry must be REG_SZ')
                if not Path(dll_path).is_file():
                    raise RuntimeError('Security DLL not found at registered path: ' + dll_path)
            except OSError as reg_error:
                raise RuntimeError('Hancom security module is not set up. Run SETUP_HANCOM_SECURITY.bat once with Hancom official Automation module.') from reg_error
            module_ok = app.RegisterModule('FilePathCheckDLL', module_name)
            if module_ok is False:
                raise RuntimeError('Hancom RegisterModule returned False. Verify DLL bitness, registry, Hancom version; not opening documents with repeated access prompts.')
            result['hancom_security_module'] = 'REGISTERED'
            try:
                app.XHwpWindows.Item(0).Visible = True
            except Exception:
                pass
            ret = app.Open(str(a.source.resolve()), 'HWPX', '')
            if ret is False:
                raise RuntimeError('Hancom Open returned False')
            save_ret = app.SaveAs(str(a.out.resolve()), 'HWPX', '')
            if not a.out.is_file() or a.out.stat().st_size < 200:
                raise RuntimeError(f'Hancom SaveAs produced no file: {save_ret!r}')
            result['open_save'] = 'PASS'
            # Hancom 2020 PDF export can require external PDF device/settings.
            # Treat unsupported export as NOT_TESTED; do not silently call this a pass.
            try:
                pdf_ret = app.SaveAs(str(a.pdf.resolve()), 'PDF', '')
                result['pdf_export'] = 'PASS' if a.pdf.is_file() and a.pdf.stat().st_size > 200 else 'NOT_TESTED'
                if result['pdf_export'] != 'PASS':
                    result['pdf_error'] = 'SaveAs PDF did not produce usable file (' + repr(pdf_ret) + ')'
            except Exception as err:
                result['pdf_error'] = repr(err)
        if not a.out.exists():
            raise RuntimeError('COM did not produce native save result')
        _, expected = build_document(scenario, fmt)
        result['structure'] = open_and_check(a.out, expected)
        if fmt == 'docx':
            from tests.generators.business_docs.preservation import assert_docx_preserved
            result['data_preservation'] = assert_docx_preserved(a.source, a.out)
        result['archive'] = audit_archive(a.out, expect_image=scenario.image)
        result['semantic'] = 'PASS'
        result['status'] = 'PASS'
        return 0
    except Exception:
        result['status'] = 'FAIL'
        result['error'] = traceback.format_exc()
        return 2
    finally:
        if opened is not None:
            try: opened.Close(SaveChanges=False)
            except Exception: pass
        if app is not None:
            try:
                if fmt=='hwpx': app.Clear(1)
                app.Quit()
            except Exception: pass
        CoUninitialize()
        print(json.dumps(result, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    raise SystemExit(main())
