from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.similarity import _build_reference_from_row, _collect_reference_rows, _dataset_paths
from app.services.sound_dna import FEATURE_ORDER, vectorize

MODEL_DIR = Path(__file__).resolve().parents[1] / "app" / "data" / "models"
REPORT_JSON_PATH = MODEL_DIR / "data_quality_report.json"
REPORT_MD_PATH = MODEL_DIR / "data_quality_report.md"


@dataclass
class OutlierSummary:
    rows_with_any_outlier: int
    row_outlier_ratio: float
    outliers_by_feature: dict[str, int]


@dataclass
class ClusterBalanceSummary:
    cluster_count: int
    min_cluster_size: int
    max_cluster_size: int
    imbalance_ratio: float
    counts: dict[str, int]


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])

    q_clamped = max(0.0, min(1.0, q))
    index = (len(ordered) - 1) * q_clamped
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return float(ordered[lower])

    blend = index - lower
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * blend)


def _first_non_empty(row: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _safe_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _analyze_outliers(matrix: np.ndarray) -> OutlierSummary:
    if matrix.size == 0:
        return OutlierSummary(rows_with_any_outlier=0, row_outlier_ratio=0.0, outliers_by_feature={name: 0 for name in FEATURE_ORDER})

    q1 = np.percentile(matrix, 25, axis=0)
    q3 = np.percentile(matrix, 75, axis=0)
    iqr = q3 - q1
    iqr = np.where(iqr == 0, 1e-9, iqr)

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    mask = (matrix < lower) | (matrix > upper)
    outliers_by_feature = {
        FEATURE_ORDER[i]: int(np.sum(mask[:, i])) for i in range(mask.shape[1])
    }
    rows_with_any_outlier = int(np.sum(np.any(mask, axis=1)))
    row_outlier_ratio = rows_with_any_outlier / float(len(matrix)) if len(matrix) else 0.0

    return OutlierSummary(
        rows_with_any_outlier=rows_with_any_outlier,
        row_outlier_ratio=row_outlier_ratio,
        outliers_by_feature=outliers_by_feature,
    )


def _analyze_cluster_balance(matrix: np.ndarray, cluster_count: int) -> ClusterBalanceSummary:
    if matrix.size == 0:
        return ClusterBalanceSummary(
            cluster_count=0,
            min_cluster_size=0,
            max_cluster_size=0,
            imbalance_ratio=0.0,
            counts={},
        )

    effective_clusters = max(1, min(cluster_count, len(matrix)))
    scaler = StandardScaler()
    matrix_scaled = scaler.fit_transform(matrix)

    kmeans = KMeans(n_clusters=effective_clusters, random_state=42, n_init=20)
    labels = kmeans.fit_predict(matrix_scaled)

    counter = Counter(int(label) for label in labels)
    counts = {str(cluster_id): int(counter.get(cluster_id, 0)) for cluster_id in range(effective_clusters)}
    min_cluster = min(counts.values()) if counts else 0
    max_cluster = max(counts.values()) if counts else 0
    imbalance_ratio = (max_cluster / float(max(1, min_cluster))) if counts else 0.0

    return ClusterBalanceSummary(
        cluster_count=effective_clusters,
        min_cluster_size=min_cluster,
        max_cluster_size=max_cluster,
        imbalance_ratio=imbalance_ratio,
        counts=counts,
    )


def _analyze_raw_sources(paths: list[Path]) -> dict[str, dict[str, object]]:
    required_numeric = [
        "tempo",
        "danceability",
        "energy",
        "loudness",
        "speechiness",
        "acousticness",
        "instrumentalness",
        "liveness",
        "valence",
    ]

    report: dict[str, dict[str, object]] = {}
    for path in paths:
        if not path.exists():
            report[str(path)] = {
                "exists": False,
                "rows_total": 0,
                "missing_fields": {},
                "invalid_numeric_fields": {},
                "missing_track_id": 0,
                "invalid_tempo_rows": 0,
            }
            continue

        rows_total = 0
        missing_fields: Counter[str] = Counter()
        invalid_numeric_fields: Counter[str] = Counter()
        missing_track_id = 0
        invalid_tempo_rows = 0

        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows_total += 1

                track_id = _first_non_empty(row, ["track_id", "id"])
                if not track_id:
                    missing_track_id += 1

                for field in ["track_name", "artist_name", "track_artist", "popularity", "track_popularity", *required_numeric]:
                    value = row.get(field)
                    if value is None or str(value).strip() == "":
                        missing_fields[field] += 1

                for field in required_numeric:
                    raw = row.get(field)
                    if raw is None or str(raw).strip() == "":
                        continue
                    if _safe_float(str(raw)) is None:
                        invalid_numeric_fields[field] += 1

                normalized = _build_reference_from_row(row)
                if normalized is None:
                    invalid_tempo_rows += 1

        report[str(path)] = {
            "exists": True,
            "rows_total": rows_total,
            "missing_fields": dict(missing_fields),
            "invalid_numeric_fields": dict(invalid_numeric_fields),
            "missing_track_id": missing_track_id,
            "invalid_tempo_rows": invalid_tempo_rows,
        }

    return report


def _threshold_report(min_popularity: float, cluster_count: int) -> dict[str, object]:
    refs, stats = _collect_reference_rows(min_popularity=min_popularity)
    if not refs:
        return {
            "min_popularity": min_popularity,
            "rows_kept": 0,
            "rows_after_filter": 0,
            "rows_deduped": 0,
            "dedupe_retention_ratio": 0.0,
            "track_id_title_collisions": 0,
            "outliers": asdict(_analyze_outliers(np.zeros((0, len(FEATURE_ORDER)), dtype=np.float32))),
            "cluster_balance": asdict(_analyze_cluster_balance(np.zeros((0, len(FEATURE_ORDER)), dtype=np.float32), cluster_count)),
        }

    matrix = np.vstack([np.array(vectorize(ref["features"]), dtype=np.float32) for ref in refs])
    popularity_values = [float(ref.get("popularity", 0.0)) for ref in refs]

    outliers = _analyze_outliers(matrix)
    cluster_balance = _analyze_cluster_balance(matrix, cluster_count)

    rows_after_filter = int(stats.get("rows_after_filter", len(refs)))
    rows_deduped = int(stats.get("rows_deduped", 0))
    dedupe_retention_ratio = (len(refs) / float(max(1, rows_after_filter)))

    return {
        "min_popularity": min_popularity,
        "rows_kept": len(refs),
        "rows_after_filter": rows_after_filter,
        "rows_deduped": rows_deduped,
        "dedupe_retention_ratio": dedupe_retention_ratio,
        "track_id_title_collisions": int(stats.get("track_id_title_collisions", 0)),
        "popularity_stats": {
            "min": float(min(popularity_values)),
            "max": float(max(popularity_values)),
            "mean": float(sum(popularity_values) / len(popularity_values)),
            "median": float(median(popularity_values)),
            "p10": _percentile(popularity_values, 0.10),
            "p25": _percentile(popularity_values, 0.25),
            "p50": _percentile(popularity_values, 0.50),
            "p75": _percentile(popularity_values, 0.75),
            "p90": _percentile(popularity_values, 0.90),
        },
        "outliers": asdict(outliers),
        "cluster_balance": asdict(cluster_balance),
    }


def _choose_recommended_threshold(candidates: list[dict[str, object]]) -> tuple[float, str]:
    quality_balanced = [
        row
        for row in candidates
        if int(row.get("rows_kept", 0)) >= 50000
        and float(row.get("outliers", {}).get("row_outlier_ratio", 1.0)) <= 0.38
        and float(row.get("cluster_balance", {}).get("imbalance_ratio", 999.0)) <= 7.0
    ]

    if quality_balanced:
        chosen = max(quality_balanced, key=lambda row: float(row.get("min_popularity", 0.0)))
        return float(chosen["min_popularity"]), (
            "Selected highest threshold that keeps >=50k tracks while maintaining "
            "outlier ratio <= 0.38 and cluster imbalance <= 7.0."
        )

    coverage_viable = [
        row for row in candidates
        if int(row.get("rows_kept", 0)) >= 40000
    ]
    if coverage_viable:
        chosen = max(coverage_viable, key=lambda row: int(row.get("rows_kept", 0)))
        return float(chosen["min_popularity"]), (
            "No threshold met strict balance constraints; selected option with strongest retained coverage."
        )

    fallback = max(candidates, key=lambda row: int(row.get("rows_kept", 0))) if candidates else {"min_popularity": 30.0}
    return float(fallback["min_popularity"]), "Fallback to maximum retained tracks due low-volume candidates."


def write_markdown_report(report: dict[str, object], output_path: Path) -> None:
    lines: list[str] = []
    lines.append("# Dataset Quality Audit")
    lines.append("")
    lines.append(f"Generated: {report['generated_at_utc']}")
    lines.append(f"Recommended SPOTIFY_MIN_POPULARITY: {report['recommendation']['recommended_min_popularity']}")
    lines.append("")

    lines.append("## Data Sources")
    for path in report["dataset_paths"]:
        lines.append(f"- {path}")
    lines.append("")

    lines.append("## Raw Missing/Validation Checks")
    for path, stats in report["raw_source_checks"].items():
        lines.append(f"### {path}")
        lines.append(f"- exists: {stats['exists']}")
        lines.append(f"- rows_total: {stats['rows_total']}")
        lines.append(f"- missing_track_id: {stats['missing_track_id']}")
        lines.append(f"- invalid_tempo_rows: {stats['invalid_tempo_rows']}")
        lines.append("")

    lines.append("## Threshold Comparison")
    for row in report["threshold_comparison"]:
        lines.append(
            f"- threshold={row['min_popularity']}: kept={row['rows_kept']}, "
            f"deduped={row['rows_deduped']}, retention={row['dedupe_retention_ratio']:.4f}, "
            f"outlier_ratio={row['outliers']['row_outlier_ratio']:.4f}, "
            f"cluster_imbalance={row['cluster_balance']['imbalance_ratio']:.2f}"
        )
    lines.append("")

    lines.append("## Recommendation")
    lines.append(f"- {report['recommendation']['rationale']}")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    cluster_count = int(os.getenv("STYLE_CLUSTER_COUNT", "10"))
    cluster_count = max(8, min(cluster_count, 12))

    paths = _dataset_paths()
    raw_checks = _analyze_raw_sources(paths)

    thresholds = [20.0, 25.0, 30.0, 35.0, 40.0]
    threshold_rows = [_threshold_report(min_popularity=value, cluster_count=cluster_count) for value in thresholds]

    recommended_threshold, rationale = _choose_recommended_threshold(threshold_rows)

    recommendation_detail = next(
        (row for row in threshold_rows if float(row.get("min_popularity", -1)) == recommended_threshold),
        None,
    )

    report: dict[str, object] = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "cluster_count": cluster_count,
        "dataset_paths": [str(path) for path in paths],
        "raw_source_checks": raw_checks,
        "threshold_comparison": threshold_rows,
        "recommendation": {
            "recommended_min_popularity": recommended_threshold,
            "rationale": rationale,
            "details": recommendation_detail,
        },
    }

    REPORT_JSON_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown_report(report, REPORT_MD_PATH)

    print(f"Saved: {REPORT_JSON_PATH}")
    print(f"Saved: {REPORT_MD_PATH}")
    print(f"Recommended SPOTIFY_MIN_POPULARITY={recommended_threshold}")


if __name__ == "__main__":
    main()
