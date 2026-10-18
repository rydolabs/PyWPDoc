# -*- coding: utf-8 -*-
"""One-click, isolated Windows QA bootstrap for PyWPDoc (version-independent).

Creates <kit>/.venv, installs dependencies into that interpreter (never
system Python), checks actual imports, and runs the existing QA runner.
All setup failures are recorded and packed for analysis.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from datetime import datetime
import subprocess
import sys
import traceback
import venv
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
ENV = ROOT / '.venv'
RESULTS = ROOT / 'HWP_RC_RESULTS'
LOG = RESULTS / 'setup.log'
# Exactly one tested wheel must be present; never select an old wheel silently.
_candidates = sorted(ROOT.glob('pywpdoc-*.whl'))
WHEEL = _candidates[0] if len(_candidates) == 1 else ROOT / '__no_unique_wheel__.whl'

REQUIREMENTS = ROOT / 'requirements-qa.txt'


def venv_python():
    if os.name == 'nt':
        return ENV / 'Scripts' / 'python.exe'
    return ENV / 'bin' / 'python'


def say(message: str):
    message = str(message)
    print(message, flush=True)
    with LOG.open('a', encoding='utf-8') as output:
        output.write(message + '\n')


def command(args: list[str], *, label: str):
    say(f'[STEP] {label}')
    # Subprocess API arguments are a list: Unicode paths and spaces are safe.
    proc = subprocess.Popen(
        [str(a) for a in args], cwd=str(ROOT), stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, encoding='utf-8', errors='replace',
        env={**os.environ, 'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'PIP_NO_INPUT': '1',
             'PYTHONIOENCODING': 'utf-8'},
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        say(line.rstrip('\r\n'))
    result = proc.wait()
    say(f'[EXIT] {label}: {result}')
    return result


def pack_results():
    path = ROOT / 'HWP_RC_RESULTS.zip'
    with ZipFile(path, 'w', compression=ZIP_DEFLATED) as archive:
        for file in sorted(RESULTS.rglob('*')):
            if file.is_file():
                archive.write(file, file.relative_to(RESULTS))
    say(f'[RESULT] {path}')
    return path


def setup_failure(stage: str, message: str, exit_code: int = 3):
    say(f'[ERROR] {stage}: {message}')
    (RESULTS / 'SETUP_ERROR.txt').write_text(
        f'Stage: {stage}\nMessage: {message}\n'
        f'Log: HWP_RC_RESULTS/setup.log\n', encoding='utf-8',
    )
    (RESULTS / 'setup_status.json').write_text(json.dumps({
        'status': 'SETUP_ERROR', 'stage': stage, 'message': message,
        'venv_python': str(venv_python()), 'system_python': sys.executable,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    pack_results()
    return exit_code


def execute(offline: bool, dry_run: bool = False):
    if sys.version_info < (3, 10):
        return setup_failure('python_version',
                             'Python 3.10 or newer is required (3.11/3.12 recommended).')
    if os.name != 'nt' and not offline:
        return setup_failure('platform', 'Run Windows native QA on Windows. Use --offline for an offline check.')
    if len(_candidates) > 1 and ROOT == Path(__file__).resolve().parent:
        return setup_failure('wheel', 'Multiple PyWPDoc wheels present; keep exactly one tested version.')
    if not WHEEL.is_file():
        return setup_failure('wheel', f'Bundled wheel missing: {WHEEL.name}')
    if not REQUIREMENTS.is_file():
        return setup_failure('requirements', f'Missing dependency list: {REQUIREMENTS.name}')
    if dry_run:
        say('[DRY-RUN] No files installed. Planned isolated environment and commands:')
        say(f'  system Python: {sys.executable}')
        say(f'  target venv: {ENV}')
        say(f'  wheel: {WHEEL.name}')
        say(f'  dependencies: {REQUIREMENTS.name} (platform-aware pywin32)')
        say(f'  run: {venv_python()} run_rc_windows.py' + (' --offline' if offline else ''))
        return 0
    python = venv_python()
    if not python.is_file():
        if ENV.exists():
            return setup_failure('venv',
                'Incomplete .venv already exists. Rename that .venv directory and rerun; it will not be deleted automatically.')
        say(f'[STEP] Creating isolated venv at: {ENV}')
        try:
            venv.EnvBuilder(with_pip=True, system_site_packages=False, clear=False).create(str(ENV))
        except Exception as ex:
            return setup_failure('venv', repr(ex))
        if not python.is_file():
            return setup_failure('venv', f'Python executable not found after creation: {python}')
    else:
        say(f'[STEP] Reusing existing .venv: {python}')

    if command([python, '-m', 'pip', '--version'], label='Check pip') != 0:
        if command([python, '-m', 'ensurepip', '--upgrade'], label='Restore pip') != 0:
            return setup_failure('pip', 'pip unavailable in .venv (ensurepip failed).')

    specs = [str(WHEEL), '-r', str(REQUIREMENTS)]
    pip_cmd = [python, '-m', 'pip', 'install', '--disable-pip-version-check',
               '--no-input', '--prefer-binary', '--retries', '2', '--timeout', '20', *specs]
    if command(pip_cmd, label='Install PyWPDoc and QA dependencies in .venv') != 0:
        return setup_failure('pip_install',
            'Dependency installation failed. Check setup.log for the package/network/proxy error. '
            'Internet access may be required for python-docx, lxml, pytest, and pywin32.')
    if command([python, '-m', 'pip', 'check'], label='Check dependency consistency') != 0:
        return setup_failure('dependency_check', 'pip check reports incompatible dependencies.')

    verify = (
        'import sys, docx, pytest, lxml, pywpdoc; '
        'assert pywpdoc.__version__ == "' + WHEEL.name.split('-')[1] + '", pywpdoc.__version__; '
        'import importlib.metadata as im; '
        'assert tuple(map(int, im.version("python-docx").split(".")[:2])) >= (1, 2); '
        + ('' if offline else 'import win32com.client; ')
        + 'print("OK:", sys.executable); '
        'print("python-docx:", docx.__version__, docx.__file__); '
        'print("pywpdoc:", pywpdoc.__version__); '
        'print("pytest:", pytest.__version__); '
        'print("lxml:", lxml.__version__)'
    )
    if command([python, '-c', verify], label='Verify imports inside .venv') != 0:
        return setup_failure('imports', 'Import check failed; see setup.log. The installed package is named python-docx and imported as docx.')

    (RESULTS / 'setup_status.json').write_text(json.dumps({
        'status': 'READY', 'system_python': sys.executable,
        'venv_python': str(python), 'wheel': WHEEL.name,
        'offline': offline,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    native_cmd = [python, str(ROOT / 'run_rc_windows.py')]
    if offline:
        native_cmd.append('--offline')
    rc = command(native_cmd, label='Run integrated QA in .venv')
    # Extended tests are independent: run even if earlier QA had failures.
    extended_cmd = [python, str(ROOT / 'run_extended_windows.py')]
    if offline: extended_cmd.append('--offline')
    ext_rc = command(extended_cmd, label='Extended python-docx port and long-document QA')
    # Independent fail-closed tests always run, even after a native/extended
    # failure. This does not turn a missing Windows COM test into a PASS.
    safety_file = ROOT / 'test_compare_scope_safety_v0431rc2.py'
    if safety_file.is_file():
        safety_rc = command([python, '-m', 'pytest', '-q', str(safety_file)],
                            label='Compare scope safety regressions')
    else:
        safety_rc = 3
        say('[ERROR] Compare scope safety test file is missing from this kit.')
    # The QA runner makes HWP_RC_RESULTS.zip before returning, but zip again
    # to include the final lines of setup.log and the dependency status file.
    pack_results()
    if rc or ext_rc or safety_rc:
        say('[WARN] QA returned nonzero. Inspect HWP_RC_RESULTS.zip/results.json; '
            'native SKIP/ERROR is not a PASS.')
    else:
        say('[DONE] QA completed; review HWP_RC_RESULTS.zip before release.')
    return rc or ext_rc or safety_rc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true', help='Development-only: do not invoke Windows COM')
    parser.add_argument('--dry-run', action='store_true', help='Print setup plan without creating venv')
    args = parser.parse_args()
    if RESULTS.exists():
        # Never mix stale PASS artifacts with a new run. Preserve old logs separately.
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        previous = ROOT / ('HWP_RC_RESULTS_previous_' + stamp)
        suffix = 1
        while previous.exists():
            previous = ROOT / ('HWP_RC_RESULTS_previous_' + stamp + '_' + str(suffix))
            suffix += 1
        try:
            RESULTS.rename(previous)
        except OSError as ex:
            print('[ERROR] Cannot preserve previous results directory:', ex, flush=True)
            return 3
    RESULTS.mkdir(exist_ok=True)
    LOG.write_text('', encoding='utf-8')
    try:
        return execute(args.offline, args.dry_run)
    except Exception:
        err = traceback.format_exc()
        say(err)
        return setup_failure('unexpected_exception', err)


if __name__ == '__main__':
    sys.exit(main())
