@echo off
setlocal
cd /d "%~dp0..\..\.."
set "P=.venv-business\Scripts\python.exe"
if not exist "%P%" (
  py -3 -m venv .venv-business
  if errorlevel 1 exit /b 1
)
"%P%" -m pip install -e ".[test,unified]" pywin32
if errorlevel 1 exit /b 1
"%P%" -m pytest -q tests\business_docs\test_independent_table_separators.py
if errorlevel 1 exit /b 1
"%P%" -m tests.generators.business_docs.generate --out business_qa_results\generated_failed4 --format docx --only 01_contract 11_purchase_order 23_complex_tables 24_long_form
if errorlevel 1 exit /b 1
"%P%" -m tests.generators.business_docs.windows_review --generated business_qa_results\generated_failed4 --out business_qa_results\native_failed4 --only 01_contract 11_purchase_order 23_complex_tables 24_long_form
set "RESULT=%ERRORLEVEL%"
echo.
echo Results: business_qa_results\native_failed4\BUSINESS_NATIVE_QA_RESULTS.zip
echo Please upload that ZIP for independent review.
exit /b %RESULT%
