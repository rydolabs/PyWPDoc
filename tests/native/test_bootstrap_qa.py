"""Tests for installer orchestration; do not require Hancom or Word."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock
from zipfile import ZipFile
import bootstrap_qa as mod


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        patchers = [
            mock.patch.object(mod, 'ROOT', root),
            mock.patch.object(mod, 'ENV', root / '.venv'),
            mock.patch.object(mod, 'RESULTS', root / 'HWP_RC_RESULTS'),
            mock.patch.object(mod, 'LOG', root / 'HWP_RC_RESULTS' / 'setup.log'),
            mock.patch.object(mod, 'WHEEL', root / 'pywpdoc-0.43.1rc2-py3-none-any.whl'),
            mock.patch.object(mod, 'REQUIREMENTS', root / 'requirements-qa.txt'),
        ]
        for patch in patchers:
            patch.start(); self.addCleanup(patch.stop)
        mod.RESULTS.mkdir()
        mod.LOG.write_text('', encoding='utf-8')
        mod.WHEEL.write_bytes(b'mock wheel for orchestrator tests')
        mod.REQUIREMENTS.write_text('python-docx>=1.2,<2\n', encoding='utf-8')
        (root / 'test_compare_scope_safety_v0431rc2.py').write_text('# mock safety test file\n', encoding='utf-8')

    def prepare_python(self):
        p = mod.venv_python()
        p.parent.mkdir(parents=True)
        p.write_bytes(b'placeholder for fake executable')
        return p

    def test_dry_run_does_not_create_venv(self):
        self.assertEqual(mod.execute(offline=True, dry_run=True), 0)
        self.assertFalse(mod.ENV.exists())

    def test_missing_wheel_creates_error_zip(self):
        mod.WHEEL.unlink()
        self.assertEqual(mod.execute(offline=True), 3)
        with ZipFile(mod.ROOT / 'HWP_RC_RESULTS.zip') as z:
            self.assertIn('SETUP_ERROR.txt', z.namelist())
            self.assertIn('setup.log', z.namelist())

    def test_existing_venv_is_reused_and_no_global_python_pip(self):
        p = self.prepare_python()
        calls = []
        def command(args, *, label):
            calls.append((args, label))
            return 0
        with mock.patch.object(mod, 'command', side_effect=command):
            self.assertEqual(mod.execute(offline=True), 0)
        self.assertEqual(len(calls), 7)
        for args, _ in calls:
            self.assertEqual(str(args[0]), str(p))
        self.assertIn('pip', calls[1][0])
        self.assertIn(str(mod.WHEEL), list(map(str, calls[1][0])))
        self.assertTrue((mod.ROOT / 'HWP_RC_RESULTS.zip').exists())

    def test_failed_install_records_error(self):
        self.prepare_python()
        def failure(args, *, label):
            return 1 if label.startswith('Install PyWPDoc') else 0
        with mock.patch.object(mod, 'command', side_effect=failure):
            self.assertEqual(mod.execute(offline=True), 3)
        self.assertIn('pip_install', (mod.RESULTS/'SETUP_ERROR.txt').read_text())

    def test_failed_import_records_error(self):
        self.prepare_python()
        def failure(args, *, label):
            return 1 if label.startswith('Verify imports') else 0
        with mock.patch.object(mod, 'command', side_effect=failure):
            self.assertEqual(mod.execute(offline=True), 3)
        self.assertIn('imports', (mod.RESULTS/'SETUP_ERROR.txt').read_text())

    def test_failed_native_test_is_not_marked_success(self):
        self.prepare_python()
        def failure(args, *, label):
            return 2 if label.startswith('Run integrated QA') else 0
        with mock.patch.object(mod, 'command', side_effect=failure):
            self.assertEqual(mod.execute(offline=True), 2)
        self.assertEqual(__import__('json').loads((mod.RESULTS/'setup_status.json').read_text())['status'], 'READY')

    def test_windows_batch_ascii_crlf(self):
        original = Path(__file__).resolve().parent / 'RUN_WINDOWS.bat'
        data = original.read_bytes()
        data.decode('ascii')
        self.assertEqual(data.replace(b'\r\n', b'').count(b'\n'), 0)
        self.assertIn(b'cd /d "%~dp0..\\.."', data)
        self.assertIn(b'tests\\native\\run_rc_windows.py', data)
        self.assertIn(b'.venv-native\\Scripts\\python.exe', data)

    def test_requirements_match_import(self):
        path = Path(__file__).resolve().parent / 'requirements-qa.txt'
        required = path.read_text(encoding='utf-8')
        self.assertIn('python-docx>=1.2', required)
        self.assertIn('pywin32', required)
        self.assertIn('sys_platform', required)


if __name__ == '__main__':
    unittest.main(verbosity=2)
