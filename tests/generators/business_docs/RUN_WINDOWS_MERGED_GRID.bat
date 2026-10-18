@echo off
setlocal
cd /d "%~dp0..\..\.."
set "PY=.venv-business\Scripts\python.exe"
if not exist "%PY%" (
  py -3 -m venv .venv-business
  if errorlevel 1 exit /b 1
)
"%PY%" -m pip install -e ".[test,unified]" pywin32
if errorlevel 1 exit /b 1
"%PY%" -m pytest -q tests\common_api\regression\test_merged_grid_roundtrip.py tests\common_api\regression\test_word_native_merge_fixtures.py
if errorlevel 1 exit /b 1
"%PY%" -m tests.generators.business_docs.windows_merged_grid --out merge_grid_native_results
set "RESULT=%ERRORLEVEL%"
echo.
echo Please upload merge_grid_native_results\MERGE_GRID_NATIVE_QA_RESULTS.zip
exit /b %RESULT%
