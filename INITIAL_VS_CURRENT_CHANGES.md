# MusicGrowth.AI - Initial vs Current Change Summary

Last updated: 2026-04-07

## 1) Runtime and Port Cleanup

### Before

- Backend was configured to run on port 8001 in launcher, frontend proxy, and docs.
- This created confusion against the common FastAPI default of 8000.

### Now

- Backend default port is standardized to 8000.
- Frontend proxy points to backend on 8000.
- Verification script health check uses 8000.
- Documentation examples and startup instructions are aligned to 8000.
- Legacy 8001 backend listener was terminated (old Uvicorn worker process) so the app runtime is now only on 8000/5173.

### Updated files (port cleanup)

- scripts/start-dev.ps1
- frontend/vite.config.js
- scripts/verify-core.ps1
- README.md
- TEAM_QUICKSTART_WINDOWS.md

### Runtime validation

- `http://127.0.0.1:8000/api/health` returns `{ "status": "ok" }`.
- Frontend responds on `http://127.0.0.1:5173`.
- No active `LISTENING` entry remains on port 8001.

## 2) Analysis Pipeline and Quality Improvements (Initial -> Current)

### Key improvements delivered

- Safer upload pipeline with chunked writes and max-size guardrails.
- Startup security validation (required JWT secret checks).
- Dataset quality auditing and report generation.
- Clustering K retune with metric-based candidate scoring.
- Confidence calibration with reliability bins and margin signals.
- Popularity model benchmarking with leakage-aware split strategy.
- Backend + frontend smoke guardrails and one-command verification.

## 3) Accuracy and Quality Metrics

## Popularity model uplift

- Reported initial baseline in sprint brief: R2 = 0.0752.
- Current best benchmarked model (hist_gradient_boosting):
  - MAE = 10.094119
  - R2 = 0.318366
- Absolute R2 gain: 0.243166
- Relative R2 gain: 4.2336x
- MAE improvement vs mean baseline: 29.59%

Source artifact:

- backend/app/data/models/popularity_benchmark.json

## Clustering quality retune

- Selected cluster count: K = 7
- Selected candidate metrics:
  - Silhouette: 0.193483
  - Davies-Bouldin: 1.401553
  - Calinski-Harabasz: 1661.65674
- Selection respected interpretability constraints (balance and largest share).

Source artifact:

- backend/app/data/models/k_search_report.json

## Confidence calibration quality

- Raw confidence mean: 56.696
- Calibrated confidence mean: 83.581
- Reliability calibration bins loaded: true
- Global neighbor agreement prior used in calibration: 0.89703

Source artifacts:

- backend/app/data/models/dataset_quality_report.json
- backend/app/data/models/confidence_calibration.json

## 4) A/B Simulator: How It Calculates

Implementation source:

- backend/app/services/trajectory.py

## Input

- Base feature vector (14 Sound DNA features).
- User adjustments (feature deltas).
- Optional optimizer objective: similarity or opportunity.

## Feature safety and bounds

- Unit-range features are clamped to [0, 1].
- Other features are clamped by defined ranges (tempo, loudness, MFCC bounds).

Formula:

- candidate_value = clamp(feature, base_value + delta)

## Snapshot computation

Each snapshot computes:

- Style cluster (predict_style_cluster)
- Top-3 similar references (top_similar)
- Average similarity score
- Expected market demand/saturation/opportunity via membership-weighted blending

Weighted market formulas:

- demand = sum_k p_k \* demand_k
- saturation = sum_k p_k \* saturation_k
- opportunity_score = sum_k p_k \* opportunity_score_k

where p_k is cluster membership probability for cluster k.

## A/B simulation output math

- similarity_delta = after.avg_similarity - before.avg_similarity
- opportunity_delta = after.opportunity_score - before.opportunity_score
- cluster_changed = after.cluster_id != before.cluster_id

## Auto-optimizer math

- Greedy coordinate search over allowed features.
- Uses per-feature step sizes and max movement limits.
- Objective score:
  - similarity objective: avg_similarity
  - opportunity objective: opportunity_score

Optimization score formulas:

- baseline_score = objective(before_snapshot)
- optimized_score = objective(best_snapshot)
- improvement = optimized_score - baseline_score

## 5) Frontend-Visible Differences

### Before

- Confidence was shown as a single value.
- Difference cards had less explicit categorization context.

### Now

- Cluster confidence UI shows calibrated confidence and raw confidence.
- Difference cards display explicit tags (KEY_DIFFERENTIATOR, OPPORTUNITY, NORMAL).
- API contract smoke checks ensure required analysis fields stay stable.

## 6) Notes

- Current recency still uses 2018/2019 Spotify snapshots unless newer files are provided.
- With new dataset files, rerun build/train/audit to regenerate model artifacts and metrics.
