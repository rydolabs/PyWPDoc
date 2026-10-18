@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_LOCAL_TESTS.ps1" %*
exit /b %ERRORLEVEL%
