@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0..\.."
if errorlevel 1 (
  echo [ERROR] Could not find the extracted PyWPDoc folder.
  pause
  exit /b 2
)

set "PYBOOT=py -3"
py -3 -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>nul
if errorlevel 1 (
  set "PYBOOT=python"
  python -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Install Python 3.10+ first, then double-click this file again.
    pause
    exit /b 2
  )
)

set "ENV=tests\showcase\.venv-showcase"
if not exist "%ENV%\Scripts\python.exe" (
  echo [1/3] Creating isolated Python environment...
  %PYBOOT% -m venv "%ENV%"
  if errorlevel 1 goto :setup_failed
)

echo [2/3] Installing THIS CHECKOUT and screenshot dependencies...
"%ENV%\Scripts\python.exe" -m pip install --disable-pip-version-check --no-input -e . "pywin32>=306" "PyMuPDF>=1.24,<2"
if errorlevel 1 goto :setup_failed

echo [3/3] Generating safe sample documents, Word/Hancom PDF renders and PNG previews...
"%ENV%\Scripts\python.exe" tests\showcase\run_showcase.py
set "RESULT=%ERRORLEVEL%"
echo.
echo Result code: %RESULT%
echo ZIP files are in tests\showcase\OUTPUT\
echo Please upload the newest SHOWCASE_RESULTS_*.zip in this chat.
echo Never run this on private documents: samples use synthetic text only.
pause
exit /b %RESULT%

:setup_failed
echo.
echo [ERROR] Python setup failed. Check Internet access and installed Python.
echo No existing document was changed, and nothing was published.
pause
exit /b 3
