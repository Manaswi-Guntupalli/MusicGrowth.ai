# Team Quick Start (Windows)

Use this when you want the project running fast with minimum confusion.

## A. One-Time Install

1. Install Python 3.11+
2. Install Node.js 18+
3. Install MongoDB Community Server

## B. Open 2 Terminals

- Terminal 1 for backend
- Terminal 2 for frontend

## C. Preflight Check (Optional but Recommended)

From project root:

- powershell -ExecutionPolicy Bypass -File .\scripts\preflight.ps1

You should see PASS lines for:

- Python
- Node
- npm
- Spotify CSV files

## D. Start MongoDB

If installed as service, ensure it is running.

Quick check:

- mongosh

If it opens, MongoDB is running.

## E. Start Backend (Terminal 1)

From project root:

- cd backend
- ..\.venv\Scripts\activate
- python -m pip install -r requirements.txt
- python -m uvicorn app.main:app --app-dir D:/MusicGrowth.ai/backend --host 127.0.0.1 --port 8000 --reload

Expected health:

- Open new terminal and run:
- Invoke-RestMethod http://127.0.0.1:8000/api/health
- Expected result: {"status":"ok"}

## F. Start Frontend (Terminal 2)

From project root:

- cd frontend
- npm install
- npm run dev -- --host 127.0.0.1 --port 5173

Open:

- http://127.0.0.1:5173

## G. First Functional Test (UI)

1. Register a new account
2. Login
3. Upload any supported audio file
4. Click Analyze Song
5. Confirm these sections appear:

- Sound DNA
- Top Similar References
- Difference Intelligence
- Saved Analyses

## H. Supported Audio Formats

- .mp3
- .wav
- .flac
- .m4a
- .ogg

## I. Team Rules To Avoid Runtime Issues

1. Always run backend before frontend
2. Do not use port 8000 or 5173 for other apps
3. Keep both Spotify CSV files in project root:

- D:\MusicGrowth.ai\SpotifyAudioFeaturesApril2019.csv
- D:\MusicGrowth.ai\SpotifyAudioFeaturesNov2018.csv

4. Use same Python version across team if possible

## J. Common Fixes

Issue: frontend says package.json missing

- Run frontend commands from frontend folder
- Or use:
- npm --prefix D:\MusicGrowth.ai\frontend run dev -- --host 127.0.0.1 --port 5173

Issue: 401 Missing authorization token

- Login from UI before analyze

Issue: MongoDB connection fails

- Start MongoDB service
- Check with mongosh

Issue: no similar songs or weird matches

- Verify both Spotify CSV datasets exist in root
- Ensure files are not corrupted

## K. Demo-Day Startup Order (Mandatory)

1. Start MongoDB
2. Start backend
3. Verify /api/health
4. Start frontend
5. Open website and login
6. Run one sample upload before presentation
