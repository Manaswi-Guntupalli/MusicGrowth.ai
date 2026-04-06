from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core import config as _config  # noqa: F401

from app.services.similarity import (  # noqa: E402
    CONFIDENCE_CALIBRATION_PATH,
    _clamp01,
    _apply_confidence_calibration,
    _compute_cluster_distance_stats,
    _compute_raw_margin_signals,
    _dataset_paths,
    load_reference_dataset,
)
from app.services.sound_dna import FEATURE_ORDER  # noqa: E402

MODEL_DIR = Path(__file__).resolve().parents[1] / "app" / "data" / "models"
MATRIX_PATH = MODEL_DIR / "sound_dna_matrix.npy"
SCALER_PATH = MODEL_DIR / "scaler.pkl"
KMEANS_PATH = MODEL_DIR / "kmeans.pkl"


def percentile(values: np.ndarray, q: float) -> float:
    if values.size == 0:
        return 0.0
    return float(np.percentile(values, q))


def summarize_popularity(refs: list[dict]) -> dict[str, float | int]:
    pop_values = np.array([float(row.get("popularity", 0.0)) for row in refs], dtype=np.float32)
    if pop_values.size == 0:
        return {
            "count": 0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "p10": 0.0,
            "p50": 0.0,
            "p90": 0.0,
        }

    return {
        "count": int(pop_values.size),
        "min": round(float(pop_values.min()), 4),
        "max": round(float(pop_values.max()), 4),
        "mean": round(float(pop_values.mean()), 4),
        "p10": round(percentile(pop_values, 10), 4),
        "p50": round(percentile(pop_values, 50), 4),
        "p90": round(percentile(pop_values, 90), 4),
    }


def summarize_dataset(refs: list[dict]) -> dict[str, object]:
    feature_missing = 0
    invalid_feature_rows = 0
    unique_track_ids: set[str] = set()

    for row in refs:
        track_id = str(row.get("track_id", "") or "")
        if track_id:
            unique_track_ids.add(track_id)

        features = row.get("features", {})
        if not features:
            feature_missing += 1
            continue

        for name in FEATURE_ORDER:
            value = features.get(name)
            if value is None:
                invalid_feature_rows += 1
                break
            try:
                float(value)
            except (TypeError, ValueError):
                invalid_feature_rows += 1
                break

    return {
        "rows": int(len(refs)),
        "unique_track_ids": int(len(unique_track_ids)),
        "feature_missing_rows": int(feature_missing),
        "invalid_feature_rows": int(invalid_feature_rows),
    }


def summarize_recency() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for path in _dataset_paths():
        exists = path.exists()
        modified = None
        if exists:
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()

        rows.append(
            {
                "path": str(path),
                "exists": bool(exists),
                "modified_utc": modified,
            }
        )

    return {
        "datasets": rows,
        "note": "Add newer Spotify snapshots via SPOTIFY_DATASET_APRIL/SPOTIFY_DATASET_NOV or SPOTIFY_DATASET_EXTRA workflow.",
    }


def summarize_outliers(matrix: np.ndarray) -> dict[str, dict[str, float]]:
    if matrix.size == 0:
        return {}

    report: dict[str, dict[str, float]] = {}
    n = max(1, matrix.shape[0])

    for i, feature in enumerate(FEATURE_ORDER):
        col = matrix[:, i]
        q1 = float(np.percentile(col, 25))
        q3 = float(np.percentile(col, 75))
        iqr = max(q3 - q1, 1e-9)
        lower = q1 - (1.5 * iqr)
        upper = q3 + (1.5 * iqr)
        mask = (col < lower) | (col > upper)
        outlier_count = int(np.sum(mask))

        report[feature] = {
            "q1": round(q1, 6),
            "q3": round(q3, 6),
            "iqr": round(iqr, 6),
            "lower_bound": round(lower, 6),
            "upper_bound": round(upper, 6),
            "outlier_count": outlier_count,
            "outlier_ratio": round(float(outlier_count / n), 6),
        }

    return report


def summarize_cluster_balance(cluster_sizes: dict[str, int], total_rows: int) -> dict[str, float | int]:
    if not cluster_sizes:
        return {
            "min_cluster_size": 0,
            "max_cluster_size": 0,
            "min_to_max_ratio": 0.0,
            "largest_cluster_share": 0.0,
        }

    sizes = np.array(list(cluster_sizes.values()), dtype=np.float64)
    min_size = int(np.min(sizes))
    max_size = int(np.max(sizes))
    total = max(1, int(total_rows))
    return {
        "min_cluster_size": min_size,
        "max_cluster_size": max_size,
        "min_to_max_ratio": round(float(min_size / max(max_size, 1)), 6),
        "largest_cluster_share": round(float(max_size / total), 6),
    }


def compute_confidence_stats(matrix_scaled: np.ndarray, kmeans: KMeans) -> dict[str, object]:
    labels, raw_confidence, margin_confidence = _compute_raw_margin_signals(matrix_scaled, kmeans)
    cluster_to_indices: dict[int, list[int]] = {int(i): [] for i in range(int(kmeans.n_clusters))}
    for idx, cid in enumerate(labels):
        cluster_to_indices[int(cid)].append(idx)

    distance_stats = _compute_cluster_distance_stats(matrix_scaled, kmeans, cluster_to_indices)

    confidence_calibration: dict[str, object] | None = None
    if CONFIDENCE_CALIBRATION_PATH.exists():
        try:
            with CONFIDENCE_CALIBRATION_PATH.open("r", encoding="utf-8") as f:
                confidence_calibration = json.load(f)
        except Exception:
            confidence_calibration = None

    raw_conf: list[float] = []
    calibrated_conf: list[float] = []

    for idx in range(len(matrix_scaled)):
        raw = _clamp01(float(raw_confidence[idx]))
        margin_conf = _clamp01(float(margin_confidence[idx]))

        distances = np.linalg.norm(kmeans.cluster_centers_ - matrix_scaled[idx], axis=1)
        cid = int(labels[idx])

        nearest = float(np.min(distances))

        ds = distance_stats.get(cid, {"p50": nearest, "p90": nearest + 1e-6})
        p50 = max(float(ds.get("p50", nearest)), 1e-6)
        p90 = max(float(ds.get("p90", p50 + 1e-6)), p50 + 1e-6)
        spread = max(p90 - p50, 1e-6)
        compactness = float(1.0 / (1.0 + np.exp((nearest - p50) / (spread * 1.2))))

        pre_calibration = _clamp01((0.7 * raw) + (0.3 * margin_conf))
        reliability = _apply_confidence_calibration(pre_calibration, confidence_calibration)
        calibrated = _clamp01((0.85 * reliability) + (0.15 * compactness))

        raw_conf.append(raw * 100.0)
        calibrated_conf.append(calibrated * 100.0)

    raw_arr = np.array(raw_conf, dtype=np.float32)
    cal_arr = np.array(calibrated_conf, dtype=np.float32)

    return {
        "raw": {
            "mean": round(float(raw_arr.mean()), 3),
            "median": round(percentile(raw_arr, 50), 3),
            "p90": round(percentile(raw_arr, 90), 3),
            "max": round(float(raw_arr.max()), 3),
        },
        "calibrated": {
            "mean": round(float(cal_arr.mean()), 3),
            "median": round(percentile(cal_arr, 50), 3),
            "p90": round(percentile(cal_arr, 90), 3),
            "p95": round(percentile(cal_arr, 95), 3),
            "max": round(float(cal_arr.max()), 3),
        },
        "calibration_bins_loaded": bool(confidence_calibration),
    }


def evaluate_k_candidates(matrix_scaled: np.ndarray, k_min: int, k_max: int, sample_size: int) -> list[dict[str, float | int]]:
    rng = np.random.RandomState(42)
    n = len(matrix_scaled)
    if n == 0:
        return []

    size = min(sample_size, n)
    idx = rng.choice(n, size=size, replace=False)
    X = matrix_scaled[idx]

    report: list[dict[str, float | int]] = []
    for k in range(k_min, k_max + 1):
        model = KMeans(n_clusters=k, random_state=42, n_init=20)
        labels = model.fit_predict(X)

        sil = float(silhouette_score(X, labels))
        db = float(davies_bouldin_score(X, labels))
        ch = float(calinski_harabasz_score(X, labels))
        counts = Counter(labels.tolist())
        balance = float(min(counts.values()) / max(counts.values()))

        report.append(
            {
                "k": int(k),
                "silhouette": round(sil, 5),
                "davies_bouldin": round(db, 5),
                "calinski_harabasz": round(ch, 3),
                "size_balance": round(balance, 5),
            }
        )

    report.sort(key=lambda row: row["silhouette"], reverse=True)
    return report


def build_markdown_summary(report: dict[str, object]) -> str:
    dataset = report.get("dataset", {}) if isinstance(report, dict) else {}
    popularity = report.get("popularity", {}) if isinstance(report, dict) else {}
    current_model = report.get("current_model", {}) if isinstance(report, dict) else {}
    confidence = current_model.get("confidence", {}) if isinstance(current_model, dict) else {}
    cluster_balance = current_model.get("cluster_balance", {}) if isinstance(current_model, dict) else {}
    recency = report.get("recency", {}) if isinstance(report, dict) else {}
    k_sweep = report.get("k_sweep", []) if isinstance(report, dict) else []

    lines = [
        "# Dataset Quality Report",
        "",
        "## Dataset",
        f"- Rows: {dataset.get('rows', 0)}",
        f"- Unique track IDs: {dataset.get('unique_track_ids', 0)}",
        f"- Missing feature rows: {dataset.get('feature_missing_rows', 0)}",
        f"- Invalid feature rows: {dataset.get('invalid_feature_rows', 0)}",
        "",
        "## Popularity",
        f"- Min: {popularity.get('min', 0)}",
        f"- Mean: {popularity.get('mean', 0)}",
        f"- P90: {popularity.get('p90', 0)}",
        "",
        "## Cluster Balance",
        f"- Min cluster size: {cluster_balance.get('min_cluster_size', 0)}",
        f"- Max cluster size: {cluster_balance.get('max_cluster_size', 0)}",
        f"- Min/Max ratio: {cluster_balance.get('min_to_max_ratio', 0)}",
        f"- Largest share: {cluster_balance.get('largest_cluster_share', 0)}",
        "",
        "## Confidence",
        f"- Raw mean: {confidence.get('raw', {}).get('mean', 0) if isinstance(confidence, dict) else 0}",
        f"- Calibrated mean: {confidence.get('calibrated', {}).get('mean', 0) if isinstance(confidence, dict) else 0}",
        "",
        "## Data Recency",
    ]

    datasets = recency.get("datasets", []) if isinstance(recency, dict) else []
    for row in datasets:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- {row.get('path', '')}: exists={row.get('exists', False)}, modified_utc={row.get('modified_utc', None)}"
        )

    lines.extend(["", "## K Sweep (Top)"])
    for row in k_sweep[:5]:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- k={row.get('k')}: silhouette={row.get('silhouette')}, db={row.get('davies_bouldin')}, ch={row.get('calinski_harabasz')}, balance={row.get('size_balance')}"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    if not MATRIX_PATH.exists() or not SCALER_PATH.exists() or not KMEANS_PATH.exists():
        raise SystemExit(
            "Missing model artifacts. Ensure matrix/scaler/kmeans files exist in backend/app/data/models."
        )

    refs = load_reference_dataset()

    matrix = np.load(MATRIX_PATH)
    scaler = joblib.load(SCALER_PATH)
    kmeans = joblib.load(KMEANS_PATH)
    matrix_scaled = scaler.transform(matrix)
    labels = kmeans.predict(matrix_scaled)

    k_min = int(os.getenv("AUDIT_K_MIN", "5"))
    k_max = int(os.getenv("AUDIT_K_MAX", "14"))
    sample_size = int(os.getenv("AUDIT_SAMPLE_SIZE", "8000"))

    dataset_summary = summarize_dataset(refs)
    recency_summary = summarize_recency()
    popularity_summary = summarize_popularity(refs)
    cluster_sizes = {str(k): int(v) for k, v in sorted(Counter(labels.tolist()).items())}
    cluster_balance = summarize_cluster_balance(cluster_sizes, total_rows=len(matrix_scaled))
    outlier_summary = summarize_outliers(matrix)

    confidence_summary = compute_confidence_stats(matrix_scaled, kmeans)
    k_report = evaluate_k_candidates(matrix_scaled, k_min=k_min, k_max=k_max, sample_size=sample_size)

    output = {
        "dataset": dataset_summary,
        "recency": recency_summary,
        "popularity": popularity_summary,
        "outliers": outlier_summary,
        "current_model": {
            "cluster_count": int(kmeans.n_clusters),
            "cluster_sizes": cluster_sizes,
            "cluster_balance": cluster_balance,
            "confidence": confidence_summary,
        },
        "k_sweep": k_report,
    }

    output_path = Path(os.getenv("AUDIT_OUTPUT_PATH", str(MODEL_DIR / "dataset_quality_report.json")))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    markdown_path = output_path.with_suffix(".md")
    markdown_path.write_text(build_markdown_summary(output), encoding="utf-8")

    print(json.dumps(output, indent=2))
    print(f"Saved JSON report: {output_path}")
    print(f"Saved Markdown report: {markdown_path}")


if __name__ == "__main__":
    main()
