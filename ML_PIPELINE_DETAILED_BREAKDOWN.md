# MusicGrowth.AI Detailed ML Breakdown

This document explains the full pipeline from uploading a song to each analysis tab in the UI.
It is written in simple language first, then technical depth.

## 1) One-minute overview

When a user uploads a song, the app:

1. Validates file type and size.
2. Decodes audio and extracts raw signal features.
3. Converts raw features into a normalized 14-feature Sound DNA vector.
4. Predicts a style cluster using KMeans.
5. Finds top similar tracks inside that cluster using cosine similarity.
6. Computes differences versus cluster references.
7. Produces strategic paths and trajectory simulation tools.
8. Saves the full analysis in MongoDB and renders UI tabs.

## 2) End-to-end flow from upload to tabs

## 2.1 Frontend flow

- User selects an audio file and chooses segment mode:
  - `best`: highest-energy 30-second segment.
  - `full`: full track.
- Frontend sends multipart request:
  - `POST /api/analyze?segment_mode=best|full`
  - Authorization header contains JWT bearer token.
- On success, frontend stores result in state (`latestResult`) and opens Analysis view.
- History is refreshed by calling `GET /api/analyses`.

## 2.2 Backend analyze flow

- Endpoint checks extension is one of: `.mp3`, `.wav`, `.flac`, `.m4a`, `.ogg`.
- File is streamed to temp storage in chunks with hard size guard (`MAX_UPLOAD_SIZE_BYTES`).
- Audio validity is checked with `soundfile`; if that fails, a decode fallback check uses `librosa`.
- Spoken-word guardrail checks normalized features and flags likely podcast/interview audio by default.
- Frontend can explicitly override the guardrail by retrying with `allow_spoken_word=true` ("Continue Anyway").
- Main pipeline runs via `run_analysis(...)`.
- Result is saved to Mongo collection `song_analyses` with:
  - `user_id`, `filename`, `segment_mode`, `result`, `created_at`.
- Response is returned as `AnalysisResponse`.

## 3) Audio feature extraction (signal-processing stage)

This stage converts raw waveform into physical descriptors.

## 3.1 Decode and safety fallback chain

Decode order:

1. `soundfile` read
2. fallback `librosa.load`
3. fallback `audioread`

Safety checks:

- Non-empty audio
- Finite numeric samples
- RMS threshold above silence floor (`MIN_VALID_AUDIO_RMS = 1e-4`)

## 3.2 Segment selection

If `segment_mode=best`, a 30-second window is selected by scanning with 1-second hop and picking the window with highest mean RMS.

Why this helps:

- Removes low-information intros/outros.
- Focuses on the most representative energy section for clustering.

## 3.3 Raw features computed

From waveform and STFT-style framing (`FRAME_LENGTH=2048`, `HOP_LENGTH=512`), the system computes:

- Tempo (beat interval estimate from onset peaks/autocorrelation fallback)
- RMS (average energy)
- Zero crossing rate (ZCR)
- Spectral centroid
- Spectral bandwidth
- Loudness in dB (`20*log10(mean_rms)`)
- Chroma mean
- MFCC-like coefficients (DCT of log power spectrum)
- Harmonic ratio
- Beat strength (peak density proxy)
- Tempo consistency

Notes:

- MFCC-like channels are `mfcc_mean_1` to `mfcc_mean_5`.
- This pipeline avoids fragile runtime behavior by using NumPy/SciPy-heavy logic instead of deep numba-dependent calls.

## 4) Normalization to Sound DNA (feature engineering stage)

Raw descriptors are transformed into model-friendly features in ranges aligned with reference data.

## 4.1 Base Sound DNA channels

Target channels:

- tempo
- energy
- danceability
- valence
- acousticness
- instrumentalness
- liveness
- speechiness
- loudness
- mfcc_mean_1..5

## 4.2 Key engineered formulas

High-level formulas used:

- energy: weighted mix of normalized RMS, centroid, bandwidth.
- danceability: weighted mix of tempo consistency and beat strength.
- speechiness: blend of ZCR, inverse harmonicity, and MFCC vocal-presence proxy.
- acousticness: inverse brightness and inverse bandwidth, reduced by beat strength and speechiness.
- instrumentalness: inverse of speechiness.
- valence: blend of centroid, chroma, and tempo scaling.
- liveness: beat strength plus ZCR blend.

## 4.3 MFCC alignment trick

Spotify tabular datasets do not provide true MFCC columns, so the system builds deterministic MFCC proxies from core features. For uploaded audio, each MFCC channel is blended:

- 70% actual extracted MFCC
- 30% deterministic proxy

Why this is important:

- Keeps live audio and tabular Spotify references in the same 14D space.
- Reduces train/inference schema mismatch.

## 5) Cluster prediction, similarity, and confidence

## 5.1 Reference dataset and model assets

The model layer uses persisted artifacts in `backend/app/data/models/`:

- `reference_dataset.json`
- `sound_dna_matrix.npy`
- `scaler.pkl`
- `kmeans.pkl`
- `cluster_labels.json`
- `market_profile.json`

If artifacts are missing, they are rebuilt from Spotify CSV sources.

## 5.2 Cluster prediction

- Input Sound DNA vector is scaled with `StandardScaler`.
- KMeans predicts `cluster_id`.
- Human-readable cluster label is looked up from `cluster_labels.json`.

## 5.3 Confidence (current behavior)

Current production behavior uses raw confidence directly:

1. Compute distances from query to all cluster centroids.
2. Convert distances to membership-like probabilities (softmax with MAD-based temperature).
3. Take top membership and second-best membership.
4. Compute dominance score.
5. Convert to display-friendly confidence.

Current returned values:

- `style_cluster.confidence`
- `style_cluster.raw_confidence`

Both are now the same value in current code path.

## 5.4 Top similar tracks

- Query and reference vectors are normalized.
- Cosine similarity is computed.
- Search is scoped to predicted cluster first.
- Top 3 similar tracks are returned.
- Similarity score is mapped to percentage-like scale.

## 6) Differences, market targeting, and strategic paths

## 6.1 Differences engine

The system compares user track to mean of top similar references.

Features used for difference cards:

- tempo, energy, danceability, valence, acousticness, instrumentalness, liveness, speechiness, loudness

Each feature gets:

- song value
- reference mean
- delta percent
- interpretation text
- tag

Tags:

- `KEY_DIFFERENTIATOR`
- `OPPORTUNITY`
- `NORMAL`

Tag decision depends on delta magnitude and feature importance.

## 6.2 Market profile and targets

Per-cluster metrics include:

- demand (mean popularity)
- saturation (cluster size)
- opportunity score (demand / saturation)

`market_targets` ranks clusters by opportunity and provides movement suggestions.

Important UI note:

- Market Gap tab was removed from frontend tabs, but backend still computes and returns market metadata.

## 6.3 Strategic paths

App returns three predefined path archetypes:

- A: Mainstream Acceleration
- B: Niche Depth
- C: Hybrid Positioning

Each path includes strategy, expected outcome, tradeoff, and concrete actions.

## 7) Exactly what each analysis tab shows

## 7.1 Sound DNA tab

Shows:

- Mood and production style labels.
- Radar chart for 7 dimensions (energy, danceability, valence, acousticness, instrumentalness, liveness, speechiness).
- Numeric cards for all numeric Sound DNA values (including tempo, loudness, MFCC1..5).

## 7.2 Similar Artists tab

Shows:

- Top similar tracks from predicted cluster.
- Artist, song, cluster label, similarity progress bar.

## 7.3 Differences tab

Shows:

- Bar comparison (your value vs cluster reference mean).
- Difference cards with tag and interpretation text.

## 7.4 Creative Paths tab

Shows:

- Three strategic path cards (A/B/C).
- Optional AI summary call to `/creative-paths-ai-summary`.
- Summary cards with rationale, immediate actions, caution points, and KPIs.

## 7.5 A/B Simulator tab

Shows:

- Slider controls for adjustable features.
- Manual simulation (`/simulate-trajectory`).
- Auto-optimize (`/optimize-trajectory`) with objective:
  - Max Similarity
  - Max Opportunity

Outputs include:

- Before vs after cluster
- Similarity delta
- Opportunity delta
- Top projected similar tracks
- Local explainability panel

## 8) Trajectory simulator and optimizer internals

## 8.1 Simulation

Given base features + deltas:

1. Apply bounded adjustments by feature type.
2. Build `before` snapshot and `after` snapshot.
3. Compute:
   - `cluster_changed`
   - `similarity_delta`
   - `opportunity_delta`
4. Generate insight lines and explainability payload.

Snapshot contains:

- style cluster
- average similarity
- expected market demand/saturation/opportunity
- top similar tracks

## 8.2 Auto-optimize

Optimizer is constrained and practical:

- Feature-wise step sizes and max limits are predefined.
- Optional surrogate model seeds good candidate directions.
- Main search uses greedy coordinate updates over up to 4 passes.
- Final output includes recommended deltas and full simulation object.

## 8.3 Surrogate model (for optimization seeding)

- Model type: HistGradientBoostingRegressor (two models: similarity gain and opportunity gain).
- Learns from synthetic perturbations of sampled reference profiles.
- Current metadata file reports:
  - rows: 280
  - feature_count: 23
  - similarity_train_mae: 0.154874
  - opportunity_train_mae: 0.000118

Interpretation:

- Surrogate is a fast proposal engine, not the final scorer.
- Final accepted adjustments are always re-evaluated by full simulator pipeline.

## 9) Explainability layer details

## 9.1 Local explainability

Trajectory explainability can be generated locally with:

- summary
- why_it_changed
- tradeoffs
- next_steps
- feature_notes
- confidence (heuristic 0 to 1)
- disclaimer

## 9.2 OpenAI enhancement (optional)

If valid OpenAI key exists and call is enabled:

- Service requests strict JSON output from OpenAI.
- If OpenAI fails/unavailable, system falls back to local explainability.

Same fallback pattern is used for creative path AI summary.

## 10) Dataset details and model selection facts

From current repository artifacts:

- Reference rows: 50,000
- Unique track IDs: 50,000
- Missing feature rows: 0
- Invalid feature rows: 0

Popularity distribution (current report):

- Mean: 45.3384
- Median (p50): 43
- p90: 63

Current clustering facts:

- Selected cluster count: 7 (auto-selected)
- Largest cluster share: 0.26232
- Min/max cluster size ratio: 0.179552

Current K-search report indicates selection constraints for interpretability and balance were applied.

## 11) Popularity benchmark facts (judge-facing)

Separate benchmark artifact exists for popularity prediction models.

Current benchmark summary:

- Dataset rows used in benchmark run: 5000
- Best model: hist_gradient_boosting
- MAE: 10.094119
- R2: 0.318366
- Split strategy: group_shuffle_fallback

How to explain this clearly:

- MAE is average absolute prediction error in popularity points.
- Lower MAE is better.
- Here, error is about 10 popularity points on average.
- R2 around 0.32 means model captures some variance but is not near-perfect.

Important:

- Accuracy is usually not the primary metric for this regression target.
- For popularity regression, MAE and R2 are the right headline metrics.

## 12) Why MFCC and MFCC1 to MFCC5 are used

Simple explanation:

- MFCC features summarize timbre (tone color).
- Timbre often separates genres/styles that have similar tempo or energy.

Why first 5 coefficients:

- Lower-order MFCC coefficients carry broad spectral-shape information.
- They are compact and stable enough for clustering/similarity.
- Using 5 coefficients adds timbre detail without over-expanding dimensionality.

## 13) Practical limitations to mention honestly

- Spotify source snapshots are historical and may not represent newest trends.
- Cluster confidence is style-fit confidence, not guaranteed commercial outcome.
- Popularity benchmark is supportive analysis, not causal proof.
- Surrogate optimizer is an approximation step used for speed.
- Segment choice (`best` vs `full`) can change outcomes.

Current guardrail behavior:

- Likely spoken-word uploads (podcast/interview style) are flagged before analysis by default.
- User can still continue intentionally via explicit override to avoid blocking edge-case songs.

## 14) File map for this pipeline

Frontend:

- `frontend/src/pages/UploadPage.jsx`
- `frontend/src/pages/AnalysisPage.jsx`
- `frontend/src/pages/Dashboard.jsx`
- `frontend/src/lib/apiClient.js`

Backend API and orchestration:

- `backend/app/routers/analysis.py`
- `backend/app/services/pipeline.py`

Audio + feature engineering:

- `backend/app/services/feature_extraction.py`
- `backend/app/services/normalization.py`
- `backend/app/services/sound_dna.py`
- `backend/app/services/interpretation.py`

Model and strategy:

- `backend/app/services/similarity.py`
- `backend/app/services/strategy.py`
- `backend/app/services/trajectory.py`
- `backend/app/services/explainability.py`

Schemas and artifacts:

- `backend/app/models/schemas.py`
- `backend/app/data/models/dataset_quality_report.json`
- `backend/app/data/models/k_search_report.json`
- `backend/app/data/models/popularity_benchmark.json`
- `backend/app/data/models/POPULARITY_MODEL_CARD.md`

---

If you want, I can also generate a second version of this document in "judge presentation script" format (2 to 3 minute pitch, 30-second metric defense, and likely follow-up answers).
