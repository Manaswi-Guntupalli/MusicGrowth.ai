# Popularity Model Card

## Summary
- Selected model: hist_gradient_boosting
- MAE: 10.094119
- R2: 0.318366
- Dataset rows: 5000
- Split strategy: group_shuffle_fallback

## Data & Leakage Controls
- Features: normalized Sound DNA feature vector (14 features)
- Target: Spotify popularity
- Split enforces time-plus-artist holdout when possible, with group-split fallback

## Leaderboard
| Model | MAE | R2 | Train Rows | Test Rows |
|---|---:|---:|---:|---:|
| hist_gradient_boosting | 10.094119 | 0.318366 | 4151 | 849 |
| extra_trees | 10.128873 | 0.321561 | 4151 | 849 |
| random_forest | 10.214158 | 0.30009 | 4151 | 849 |
| mean_baseline | 14.336702 | -0.0604 | 4151 | 849 |

## Notes
- This model is intended for internal ranking/prioritization, not strict causal inference.
- Re-train whenever newer Spotify snapshots are added.
