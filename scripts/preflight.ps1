Write-Host "MusicGrowth.ai Preflight Check" -ForegroundColor Cyan
Write-Host "--------------------------------" -ForegroundColor Cyan

function Pass([string]$msg) { Write-Host "PASS: $msg" -ForegroundColor Green }
function Fail([string]$msg) { Write-Host "FAIL: $msg" -ForegroundColor Red }

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
$april = "D:\MusicGrowth.ai\SpotifyAudioFeaturesApril2019.csv"
$nov = "D:\MusicGrowth.ai\SpotifyAudioFeaturesNov2018.csv"

if (Test-Path $april) { Pass "Found SpotifyAudioFeaturesApril2019.csv" } else { Fail "Missing $april" }
if (Test-Path $nov) { Pass "Found SpotifyAudioFeaturesNov2018.csv" } else { Fail "Missing $nov" }

# Required project folders
if (Test-Path "D:\MusicGrowth.ai\backend") { Pass "Found backend folder" } else { Fail "Missing backend folder" }
if (Test-Path "D:\MusicGrowth.ai\frontend") { Pass "Found frontend folder" } else { Fail "Missing frontend folder" }

Write-Host "--------------------------------" -ForegroundColor Cyan
Write-Host "Preflight complete." -ForegroundColor Cyan
