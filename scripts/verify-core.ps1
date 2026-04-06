[CmdletBinding()]
param(
    [switch]$RequireLiveHealth
)

$ErrorActionPreference = "Stop"

function Info([string]$msg) { Write-Host "INFO: $msg" -ForegroundColor Cyan }
function Pass([string]$msg) { Write-Host "PASS: $msg" -ForegroundColor Green }
function Warn([string]$msg) { Write-Host "WARN: $msg" -ForegroundColor Yellow }

function Assert-NativeSuccess([string]$stepName) {
    if ($LASTEXITCODE -ne 0) {
        throw "$stepName failed with exit code $LASTEXITCODE"
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"
$startDevScript = Join-Path $scriptDir "start-dev.ps1"

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython) {
    $pythonExe = $venvPython
}
else {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $pythonCmd) {
        throw "Python executable not found."
    }
    $pythonExe = $pythonCmd.Source
}

Info "Project root: $projectRoot"
Info "Python executable: $pythonExe"

if (-not (Test-Path -LiteralPath $startDevScript)) {
    throw "Missing startup script: $startDevScript"
}

Info "Startup launcher dry-run smoke"
& $startDevScript -DryRun -SkipInstall -SkipPreflight -NoBrowser | Out-Null
Pass "start-dev.ps1 dry-run succeeded"

Info "Running backend regression tests"
$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = $projectRoot
Push-Location -LiteralPath $projectRoot
try {
    & $pythonExe -m pytest backend\tests -q
    Assert-NativeSuccess "Backend tests"
}
finally {
    Pop-Location
    $env:PYTHONPATH = $previousPythonPath
}
Pass "Backend tests passed"

Info "Running frontend API-contract smoke"
Push-Location -LiteralPath $frontendDir
try {
    npm run smoke:analysis-contract
    Assert-NativeSuccess "Frontend contract smoke"
}
finally {
    Pop-Location
}
Pass "Frontend contract smoke passed"

$healthUrl = "http://127.0.0.1:8000/api/health"
try {
    $health = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 5
    if ($health.status -ne "ok") {
        throw "Unexpected health payload"
    }
    Pass "Health endpoint reachable: $healthUrl"
}
catch {
    if ($RequireLiveHealth) {
        throw "Health endpoint smoke failed at $healthUrl. Start backend and retry."
    }
    Warn "Health endpoint not reachable (non-blocking). Start backend for live check: $healthUrl"
}

Pass "Core verification completed"
