# PyWPDoc local tests only. No Git commands, repository access, or publishing.
param([switch]$SkipInstall)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv = Join-Path $root '.venv'
$pythonInVenv = Join-Path $venv 'Scripts\python.exe'
Push-Location $root
try {
    if (-not (Test-Path -LiteralPath $pythonInVenv)) {
        Write-Host '[LOCAL QA] Setting up dedicated Python environment'
        python -m venv $venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create Python virtual environment.' }
    }
    if (-not $SkipInstall) {
        Write-Host '[LOCAL QA] Installing test dependencies'
        & $pythonInVenv -m pip install -e '.[test,unified]'
        if ($LASTEXITCODE -ne 0) { throw 'Could not install test dependencies.' }
    }
    Write-Host '[LOCAL QA] Running regression tests (no Git / no push)'
    & $pythonInVenv scripts/run_local_qa.py
    if ($LASTEXITCODE -ne 0) { throw 'Local QA failed. See .test-results for details.' }
    Write-Host '[LOCAL QA] Finished. Nothing was sent to GitHub.'
} finally {
    Pop-Location
}
