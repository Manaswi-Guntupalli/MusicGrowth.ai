$ErrorActionPreference = "Stop"
$script:HasFailure = $false

Write-Host "MusicGrowth.ai Preflight Check" -ForegroundColor Cyan
Write-Host "--------------------------------" -ForegroundColor Cyan

function Pass([string]$msg) { Write-Host "PASS: $msg" -ForegroundColor Green }
function Fail([string]$msg) {
    $script:HasFailure = $true
    Write-Host "FAIL: $msg" -ForegroundColor Red
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $scriptDir ".." )).Path

Pass "Project root resolved to $projectRoot"

# Python check
try {
    $py = python --version 2>&1
    Pass "Python detected ($py)"
}
catch {
    Fail "Python not found in PATH"
}

# Node check
try {
    $node = node --version 2>&1
    Pass "Node detected ($node)"
}
catch {
    Fail "Node not found in PATH"
}

# npm check
try {
    $npm = npm --version 2>&1
    Pass "npm detected ($npm)"
}
catch {
    Fail "npm not found in PATH"
}

# Required dataset files
$april = Join-Path $projectRoot "SpotifyAudioFeaturesApril2019.csv"
$nov = Join-Path $projectRoot "SpotifyAudioFeaturesNov2018.csv"

if (Test-Path -LiteralPath $april) { Pass "Found SpotifyAudioFeaturesApril2019.csv" } else { Fail "Missing $april" }
if (Test-Path -LiteralPath $nov) { Pass "Found SpotifyAudioFeaturesNov2018.csv" } else { Fail "Missing $nov" }

# Required project folders
$backendPath = Join-Path $projectRoot "backend"
$frontendPath = Join-Path $projectRoot "frontend"

if (Test-Path -LiteralPath $backendPath) { Pass "Found backend folder" } else { Fail "Missing $backendPath" }
if (Test-Path -LiteralPath $frontendPath) { Pass "Found frontend folder" } else { Fail "Missing $frontendPath" }

Write-Host "--------------------------------" -ForegroundColor Cyan

if ($script:HasFailure) {
    Write-Host "Preflight complete with failures." -ForegroundColor Red
    throw "Preflight checks failed."
}

Write-Host "Preflight complete." -ForegroundColor Cyan
