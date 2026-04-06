# Team Quick Start (Windows)

Use this when you want the project running fast with minimum confusion.

## A. One-Time Install

1. Install Python 3.11+
2. Install Node.js 18+
3. Install MongoDB Community Server

## A.1 Security Env Setup (Required)

From project root:

- Copy-Item .\.env.example .\.env

Edit `.env` and set required secret:

- JWT_SECRET_KEY=your-random-32-plus-character-secret

Optional override in current PowerShell session:

- $env:JWT_SECRET_KEY="your-random-32-plus-character-secret"

Notes:

- `JWT_SECRET_KEY` is required
- Minimum length is 32 characters
- Placeholder values are rejected at startup

## B. Start MongoDB

If installed as a service, ensure it is running.

Quick check:

- mongosh

If it opens, MongoDB is running.

## C. Single Source Of Truth Launcher

From project root, run:

- powershell -ExecutionPolicy Bypass -File .\scripts\start-dev.ps1

What this launcher does:

- Runs preflight checks
- Installs backend dependencies (pip)
- Installs frontend dependencies (npm)
- Starts backend on 127.0.0.1:8000 in a new terminal
- Starts frontend on 127.0.0.1:5173 in a new terminal
- Opens the app in your browser

Open app:

- http://127.0.0.1:5173

## D. Useful Launcher Flags

- Skip dependency installs:
- powershell -ExecutionPolicy Bypass -File .\scripts\start-dev.ps1 -SkipInstall

- Skip preflight:
- powershell -ExecutionPolicy Bypass -File .\scripts\start-dev.ps1 -SkipPreflight

- Dry run (show commands only):
- powershell -ExecutionPolicy Bypass -File .\scripts\start-dev.ps1 -DryRun

- Do not auto-open browser:
- powershell -ExecutionPolicy Bypass -File .\scripts\start-dev.ps1 -NoBrowser

## E. First Functional Test (UI)

1. Register a new account
2. Login
3. Upload any supported audio file
4. Click Analyze Song
5. Confirm these sections appear:

- Sound DNA
- Top Similar References
- Difference Intelligence
- Saved Analyses

## F. Supported Audio Formats

- .mp3
- .wav
- .flac
- .m4a
- .ogg

## G. Team Rules To Avoid Runtime Issues

1. Always start MongoDB before launcher
2. Do not use port 8000 or 5173 for other apps
3. Keep both Spotify CSV files in project root:

- .\SpotifyAudioFeaturesApril2019.csv
- .\SpotifyAudioFeaturesNov2018.csv

4. Use same Python version across team if possible

## H. Common Fixes

Issue: frontend says package.json missing

- Run launcher from project root
- Or run frontend command from frontend folder directly

Issue: 401 Missing authorization token

- Login from UI before analyze

Issue: MongoDB connection fails

- Start MongoDB service
- Check with mongosh

Issue: backend fails immediately on startup due to JWT config

- Ensure `.env` exists in project root
- Ensure `JWT_SECRET_KEY` is set (32+ chars)
- Avoid placeholder values

Issue: no similar songs or weird matches

- Verify both Spotify CSV datasets exist in project root
- Ensure files are not corrupted

Issue: upload fails with file too large

- Increase `MAX_UPLOAD_SIZE_BYTES` in `.env` if larger uploads are required
- Keep `UPLOAD_CHUNK_SIZE_BYTES` less than or equal to `MAX_UPLOAD_SIZE_BYTES`

## I. Demo-Day Startup Order (Mandatory)

1. Start MongoDB
2. Run launcher
3. Verify http://127.0.0.1:8000/api/health
4. Login and run one sample upload

## J. Debug Helpers (Copy-Paste)

Run from project root.

```powershell
$env:DEBUG_USER_ID="<USER_OBJECT_ID>"
$env:MONGO_URI="mongodb://127.0.0.1:27017"
$env:MONGO_DB_NAME="musicgrowth"

& .\.venv\Scripts\python.exe .\_debug_nonfinite.py --user-id $env:DEBUG_USER_ID --mongo-uri $env:MONGO_URI --db-name $env:MONGO_DB_NAME --limit 200
& .\.venv\Scripts\python.exe .\_debug_history_validation.py --user-id $env:DEBUG_USER_ID --mongo-uri $env:MONGO_URI --db-name $env:MONGO_DB_NAME --limit 200
& .\.venv\Scripts\python.exe .\backend\scripts\verify_popularity.py --min-popularity 35 --max-rows 50000
```

Script help:

```powershell
& .\.venv\Scripts\python.exe .\_debug_nonfinite.py --help
& .\.venv\Scripts\python.exe .\_debug_history_validation.py --help
& .\.venv\Scripts\python.exe .\backend\scripts\verify_popularity.py --help
```

## K. One-Command Regression Guardrails

From project root:

- powershell -ExecutionPolicy Bypass -File .\scripts\verify-core.ps1

This command runs:

- Startup launcher dry-run smoke
- Backend pytest suite (auth, analyze, history, schema, health)
- Frontend analysis API-contract smoke

Optional strict live-health check (requires backend running):

- powershell -ExecutionPolicy Bypass -File .\scripts\verify-core.ps1 -RequireLiveHealth
