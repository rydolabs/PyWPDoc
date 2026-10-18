@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
if errorlevel 1 exit /b 2
if not exist ".venv-native\Scripts\python.exe" (
  py -3 -m venv .venv-native
  if errorlevel 1 exit /b 2
)
".venv-native\Scripts\python.exe" -m pip install -e ".[test,unified]" pywin32
if errorlevel 1 exit /b 3
".venv-native\Scripts\python.exe" tests\native\run_rc_windows.py
set "RC=%ERRORLEVEL%"
echo.
echo Native QA exit code: %RC%
echo See tests\native\HWP_RC_RESULTS.zip
pause
exit /b %RC%
