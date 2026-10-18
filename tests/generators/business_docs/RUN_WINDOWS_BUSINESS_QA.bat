@echo off
setlocal
cd /d "%~dp0..\..\.."
if not exist ".venv-business\Scripts\python.exe" (
  py -3 -m venv .venv-business
  if errorlevel 1 exit /b 1
)
".venv-business\Scripts\python.exe" -m pip install -e ".[test,unified]" pywin32
if errorlevel 1 exit /b 1
".venv-business\Scripts\python.exe" -m pytest -q tests/business_docs
if errorlevel 1 exit /b 1
".venv-business\Scripts\python.exe" -m tests.generators.business_docs.generate --out business_qa_results\generated
if errorlevel 1 exit /b 1
".venv-business\Scripts\python.exe" -m tests.generators.business_docs.windows_review --generated business_qa_results\generated --out business_qa_results\native_windows
set RESULT=%ERRORLEVEL%
echo.
echo Review business_qa_results\native_windows\windows_results.json
exit /b %RESULT%
