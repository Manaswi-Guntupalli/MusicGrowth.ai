# Dataset Quality Audit

Generated: 2026-04-06T17:36:51.017628+00:00
Recommended SPOTIFY_MIN_POPULARITY: 30.0

## Data Sources
- D:\MusicGrowth.ai\SpotifyAudioFeaturesNov2018.csv
- D:\MusicGrowth.ai\SpotifyAudioFeaturesApril2019.csv
- D:\MusicGrowth.ai\SpotifyAudioFeatures2020.csv

## Raw Missing/Validation Checks
### D:\MusicGrowth.ai\SpotifyAudioFeaturesNov2018.csv
- exists: True
- rows_total: 116372
- missing_track_id: 0
- invalid_tempo_rows: 255

### D:\MusicGrowth.ai\SpotifyAudioFeaturesApril2019.csv
- exists: True
- rows_total: 130663
- missing_track_id: 0
- invalid_tempo_rows: 292

### D:\MusicGrowth.ai\SpotifyAudioFeatures2020.csv
- exists: True
- rows_total: 32832
- missing_track_id: 0
- invalid_tempo_rows: 0

## Threshold Comparison
- threshold=20.0: kept=98136, deduped=62114, retention=0.6124, outlier_ratio=0.3834, cluster_imbalance=4.30
- threshold=25.0: kept=83933, deduped=51312, retention=0.6206, outlier_ratio=0.3788, cluster_imbalance=5.68
- threshold=30.0: kept=70177, deduped=41176, retention=0.6302, outlier_ratio=0.3763, cluster_imbalance=6.72
- threshold=35.0: kept=57374, deduped=32580, retention=0.6378, outlier_ratio=0.3726, cluster_imbalance=8.09
- threshold=40.0: kept=46750, deduped=25883, retention=0.6436, outlier_ratio=0.3676, cluster_imbalance=8.70

## Recommendation
- Selected highest threshold that keeps >=50k tracks while maintaining outlier ratio <= 0.38 and cluster imbalance <= 7.0.
