[CmdletBinding()]
param(
    [string]$BindHost = "127.0.0.1",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [switch]$SkipPreflight,
    [switch]$SkipInstall,
    [switch]$NoBrowser,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Info([string]$msg) { Write-Host "INFO: $msg" -ForegroundColor Cyan }
function Pass([string]$msg) { Write-Host "PASS: $msg" -ForegroundColor Green }
function Warn([string]$msg) { Write-Host "WARN: $msg" -ForegroundColor Yellow }

function Get-PythonExecutable([string]$venvPythonPath) {
    if (Test-Path -LiteralPath $venvPythonPath) {
        return $venvPythonPath
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $pythonCommand) {
        return $pythonCommand.Source
    }

    throw "Python not found. Install Python 3.11+ or create .venv at project root."
}

function Test-PortInUse([int]$Port) {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    return $null -ne $listener
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$preflightScript = Join-Path $scriptDir "preflight.ps1"
$backendRequirements = Join-Path $backendDir "requirements.txt"

$pythonExe = Get-PythonExecutable -venvPythonPath $venvPython

Info "Project root: $projectRoot"
Info "Python executable: $pythonExe"

if (-not (Test-Path -LiteralPath $backendDir)) {
    throw "Missing backend folder at $backendDir"
}

if (-not (Test-Path -LiteralPath $frontendDir)) {
    throw "Missing frontend folder at $frontendDir"
}

if (-not (Test-Path -LiteralPath $backendRequirements)) {
    throw "Missing backend requirements file at $backendRequirements"
}

if (-not (Test-Path -LiteralPath $preflightScript)) {
    throw "Missing preflight script at $preflightScript"
}

if (-not $DryRun -and (Test-PortInUse -Port $BackendPort)) {
    throw "Backend port $BackendPort is already in use. Stop existing process or pick a new port."
}

if (-not $DryRun -and (Test-PortInUse -Port $FrontendPort)) {
    throw "Frontend port $FrontendPort is already in use. Stop existing process or pick a new port."
}

if (-not $SkipPreflight) {
    if ($DryRun) {
        Info "Dry run: would execute preflight script at $preflightScript"
    }
    else {
        Info "Running preflight checks"
        & $preflightScript
        Pass "Preflight checks passed"
    }
}

if (-not $SkipInstall) {
    if ($DryRun) {
        Info "Dry run: would install backend dependencies from $backendRequirements"
        Info "Dry run: would run npm install in $frontendDir"
    }
    else {
        Info "Installing backend dependencies"
        & $pythonExe -m pip install -r $backendRequirements

        Info "Installing frontend dependencies"
        Push-Location -LiteralPath $frontendDir
        try {
            npm install
        }
        finally {
            Pop-Location
        }
    }
}

$backendDirEscaped = $backendDir.Replace("'", "''")
$frontendDirEscaped = $frontendDir.Replace("'", "''")
$pythonExeEscaped = $pythonExe.Replace("'", "''")

$backendCommand = "Set-Location -LiteralPath '$backendDirEscaped'; & '$pythonExeEscaped' -m uvicorn app.main:app --app-dir '$backendDirEscaped' --host $BindHost --port $BackendPort --reload"
$frontendCommand = "Set-Location -LiteralPath '$frontendDirEscaped'; npm run dev -- --host $BindHost --port $FrontendPort"

if ($DryRun) {
    Write-Host ""
    Write-Host "Backend command:" -ForegroundColor Cyan
    Write-Host $backendCommand
    Write-Host ""
    Write-Host "Frontend command:" -ForegroundColor Cyan
    Write-Host $frontendCommand
    return
}

Info "Starting backend terminal"
$backendProc = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand -PassThru

Info "Starting frontend terminal"
$frontendProc = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCommand -PassThru

$frontendUrl = "http://$BindHost`:$FrontendPort/"
$backendDocs = "http://$BindHost`:$BackendPort/docs"

Pass "Backend started in new terminal (PID $($backendProc.Id))"
Pass "Frontend started in new terminal (PID $($frontendProc.Id))"
Pass "Frontend URL: $frontendUrl"
Pass "Backend docs: $backendDocs"

if ($NoBrowser) {
    Warn "Browser launch skipped by -NoBrowser"
}
else {
    Start-Process $frontendUrl | Out-Null
}
