# MusicGrowth.ai Full Run Guide

If you want the shortest teammate setup path, use:

- TEAM_QUICKSTART_WINDOWS.md
- scripts/preflight.ps1

This document explains exactly how to run the full website end to end:

- Landing page
- Register or Login
- Dashboard
- Song upload and analysis
- Export analysis as PDF
- Saving analysis to MongoDB

## 1. Project Layout

- frontend: React + Vite web app
- backend: FastAPI analysis API + auth + MongoDB persistence
- SpotifyAudioFeaturesApril2019.csv and SpotifyAudioFeaturesNov2018.csv: comparison reference datasets

## 2. Prerequisites

Install these first:

1. Python (3.11+ recommended)
2. Node.js (18+ recommended)
3. MongoDB Community Server (local)

Verify in terminal:

- python --version
- node --version
- npm --version

## 3. Start MongoDB

If MongoDB is installed as a Windows service, ensure it is running.

Quick check:

- mongosh

If mongosh opens, MongoDB is running.

Default connection used by this app:

- mongodb://127.0.0.1:27017
- database name: musicgrowth

## 4. Backend Setup and Run

Open terminal 1.

Go to backend folder:

- cd D:\MusicGrowth.ai\backend

Create virtual environment once:

- python -m venv ..\.venv

Activate venv:

- D:\MusicGrowth.ai\.venv\Scripts\activate

Install backend dependencies:

- python -m pip install -r requirements.txt

Run backend API:

- python -m uvicorn app.main:app --app-dir D:/MusicGrowth.ai/backend --host 127.0.0.1 --port 8001 --reload

Health check in another terminal:

- Invoke-RestMethod http://127.0.0.1:8001/api/health

Expected:

- {"status":"ok"}

## 5. Frontend Setup and Run

Open terminal 2.

Go to frontend folder:

- cd D:\MusicGrowth.ai\frontend

Install frontend dependencies:

- npm install

Run frontend:

- npm run dev -- --host 127.0.0.1 --port 5173

Open in browser:

- http://127.0.0.1:5173

## 6. Full App Flow (What You Should See)

1. Landing page appears first
2. Register or Login card appears
3. After login, dashboard appears
4. Upload a song with the Choose File button
5. Click Analyze Song
6. Sound DNA, Similar References, Differences, Market Gaps, and Strategic Paths appear
7. Export as PDF button is available on the Analysis page
8. Saved Analyses section updates automatically

## 7. MongoDB Data That Gets Saved

Two collections are used:

- users
  - name
  - email (unique)
  - password_hash

- song_analyses
  - user_id
  - filename
  - segment_mode
  - result (full analysis JSON)
  - created_at

Indexes are created on startup for:

- users.email (unique)
- song_analyses.user_id
- song_analyses.created_at

## 8. Dataset Used for Comparison

The similarity engine reads these CSV files from workspace root:

- D:\MusicGrowth.ai\SpotifyAudioFeaturesApril2019.csv
- D:\MusicGrowth.ai\SpotifyAudioFeaturesNov2018.csv

Behavior:

- Deduplicates using track_id
- Filters low popularity tracks (default minimum 35)
- Computes cosine similarity against normalized features

Optional environment variables:

- SPOTIFY_DATASET_APRIL (override path)
- SPOTIFY_DATASET_NOV (override path)
- SPOTIFY_MIN_POPULARITY (number, default 35)

## 9. Optional Environment Variables

You can set these before running backend:

- MONGO_URI (default mongodb://127.0.0.1:27017)
- MONGO_DB_NAME (default musicgrowth)
- JWT_SECRET_KEY (change this in production)
- JWT_EXPIRE_MINUTES (default 43200)
- SPOTIFY_DATASET_APRIL
- SPOTIFY_DATASET_NOV
- SPOTIFY_MIN_POPULARITY

PowerShell example:

- $env:MONGO_URI="mongodb://127.0.0.1:27017"
- $env:MONGO_DB_NAME="musicgrowth"
- $env:JWT_SECRET_KEY="replace-with-strong-secret"

## 10. One-Command Smoke Tests

Register:

- Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/api/auth/register -ContentType application/json -Body '{"name":"Test","email":"test1@musicgrowth.ai","password":"demo1234"}'

Analyze with token:

1. Save token from register response as TOKEN
2. Run:

- curl.exe -X POST "http://127.0.0.1:8001/api/analyze?segment_mode=best" -H "Authorization: Bearer TOKEN" -F "file=@D:/MusicGrowth.ai/dark_horse_remix.mp3"

Get saved analyses:

- Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8001/api/analyses -Headers @{ Authorization = "Bearer TOKEN" }

## 11. Common Issues and Fixes

Issue: frontend says package.json not found

Fix:

- Run commands from D:\MusicGrowth.ai\frontend
- Or use npm --prefix D:\MusicGrowth.ai\frontend run dev -- --host 127.0.0.1 --port 5173

Issue: 401 Missing authorization token

Fix:

- Login first in UI
- Or send Authorization: Bearer TOKEN header in API calls

Issue: backend cannot connect to MongoDB

Fix:

- Start MongoDB service
- Verify MONGO_URI is correct
- Test with mongosh

Issue: CSV dataset not found

Fix:

- Ensure both Spotify CSV files are in D:\MusicGrowth.ai
- Or set SPOTIFY_DATASET_APRIL and SPOTIFY_DATASET_NOV

Issue: history count seems stuck at 20

Fix:

- History endpoint now returns all analyses for the user (sorted newest first)
- Refresh History page after backend restart to pick up latest code

## 12. Exact Startup Order (Recommended Every Time)

1. Start MongoDB
2. Start backend on port 8001
3. Start frontend on port 5173
4. Open website
5. Register or Login
6. Upload and analyze song

That is the full production-like local run flow for this project.
