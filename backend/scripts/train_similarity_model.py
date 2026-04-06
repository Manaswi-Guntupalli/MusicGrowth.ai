from __future__ import annotations

from collections import Counter
import json
import os
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core import config as _config  # noqa: F401

from app.services.similarity import (
    CLUSTER_LABELS_PATH,
    K_SEARCH_REPORT_PATH,
    KMEANS_PATH,
    MARKET_PROFILE_PATH,
    MATRIX_PATH,
    REFERENCE_DATASET_PATH,
    SCALER_PATH,
    _compute_market_profile,
    _generate_cluster_labels,
)


def _normalize_metric(values: list[float], invert: bool = False) -> list[float]:
    if not values:
        return []

    arr = np.array(values, dtype=np.float64)
    lo = float(arr.min())
    hi = float(arr.max())
    if hi - lo <= 1e-12:
        normalized = np.ones_like(arr)
    else:
        normalized = (arr - lo) / (hi - lo)

    if invert:
        normalized = 1.0 - normalized

    return [float(x) for x in normalized]


def _evaluate_k_candidates(
    matrix_scaled: np.ndarray,
    k_values: list[int],
    *,
    sample_size: int,
    interp_min_balance: float,
    interp_max_largest_share: float,
) -> list[dict[str, float | int | bool]]:
    n = len(matrix_scaled)
    if n == 0:
        return []

    rng = np.random.RandomState(42)
    chosen_size = min(sample_size, n)
    idx = rng.choice(n, size=chosen_size, replace=False)
    X = matrix_scaled[idx]

    rows: list[dict[str, float | int | bool]] = []
    for k in k_values:
        model = KMeans(n_clusters=k, random_state=42, n_init=20)
        labels = model.fit_predict(X)

        sil = float(silhouette_score(X, labels))
        db = float(davies_bouldin_score(X, labels))
        ch = float(calinski_harabasz_score(X, labels))

        counts = Counter(labels.tolist())
        sizes = np.array(list(counts.values()), dtype=np.float64)
        size_balance = float(sizes.min() / max(sizes.max(), 1.0))
        largest_share = float(sizes.max() / max(len(labels), 1))
        interpretable = bool(
            size_balance >= interp_min_balance and largest_share <= interp_max_largest_share
        )

        rows.append(
            {
                "k": int(k),
                "silhouette": sil,
                "davies_bouldin": db,
                "calinski_harabasz": ch,
                "size_balance": size_balance,
                "largest_share": largest_share,
                "interpretable": interpretable,
            }
        )

    sil_norm = _normalize_metric([float(r["silhouette"]) for r in rows], invert=False)
    db_norm = _normalize_metric([float(r["davies_bouldin"]) for r in rows], invert=True)
    ch_norm = _normalize_metric([float(r["calinski_harabasz"]) for r in rows], invert=False)
    bal_norm = _normalize_metric([float(r["size_balance"]) for r in rows], invert=False)

    for i, row in enumerate(rows):
        base_score = (0.40 * sil_norm[i]) + (0.25 * db_norm[i]) + (0.20 * ch_norm[i]) + (0.15 * bal_norm[i])
        if not bool(row["interpretable"]):
            base_score -= 0.15
        row["score"] = float(base_score)

    rows.sort(key=lambda r: float(r["score"]), reverse=True)
    return rows


def _select_cluster_count(matrix_scaled: np.ndarray) -> tuple[int, dict[str, object]]:
    raw = (os.getenv("STYLE_CLUSTER_COUNT") or "").strip()
    interp_min_balance = float(os.getenv("K_INTERP_MIN_BALANCE", "0.18"))
    interp_max_largest_share = float(os.getenv("K_INTERP_MAX_LARGEST_SHARE", "0.32"))

    if raw and raw.lower() != "auto":
        explicit = int(raw)
        explicit = max(8, min(explicit, 16))
        report = {
            "selection_mode": "explicit",
            "selected_k": int(explicit),
            "constraints": {
                "interp_min_balance": interp_min_balance,
                "interp_max_largest_share": interp_max_largest_share,
            },
            "candidates": [],
        }
        return explicit, report

    k_min = int(os.getenv("K_SEARCH_MIN", "6"))
    k_max = int(os.getenv("K_SEARCH_MAX", "16"))
    if k_max < k_min:
        k_max = k_min
    k_values = [k for k in range(k_min, k_max + 1) if 4 <= k <= max(4, len(matrix_scaled) - 1)]
    if not k_values:
        k_values = [10]

    sample_size = int(os.getenv("K_SEARCH_SAMPLE_SIZE", "12000"))
    evaluated = _evaluate_k_candidates(
        matrix_scaled,
        k_values,
        sample_size=sample_size,
        interp_min_balance=interp_min_balance,
        interp_max_largest_share=interp_max_largest_share,
    )
    if not evaluated:
        return 10, {"selection_mode": "auto", "selected_k": 10, "constraints": {}, "candidates": []}

    interpretable = [row for row in evaluated if bool(row.get("interpretable", False))]
    winner = interpretable[0] if interpretable else evaluated[0]

    report = {
        "selection_mode": "auto",
        "selected_k": int(winner["k"]),
        "constraints": {
            "interp_min_balance": interp_min_balance,
            "interp_max_largest_share": interp_max_largest_share,
            "k_search_min": k_min,
            "k_search_max": k_max,
            "k_search_sample_size": sample_size,
        },
        "candidates": [
            {
                "k": int(row["k"]),
                "silhouette": round(float(row["silhouette"]), 6),
                "davies_bouldin": round(float(row["davies_bouldin"]), 6),
                "calinski_harabasz": round(float(row["calinski_harabasz"]), 6),
                "size_balance": round(float(row["size_balance"]), 6),
                "largest_share": round(float(row["largest_share"]), 6),
                "interpretable": bool(row["interpretable"]),
                "score": round(float(row["score"]), 6),
            }
            for row in evaluated
        ],
    }

    return int(winner["k"]), report


def main() -> None:
    if not MATRIX_PATH.exists() or not SCALER_PATH.exists() or not REFERENCE_DATASET_PATH.exists():
        raise FileNotFoundError(
            "Missing training artifacts. Run backend/scripts/build_reference_dataset.py first."
        )

    with REFERENCE_DATASET_PATH.open("r", encoding="utf-8") as f:
        refs = json.load(f)

    matrix = np.load(MATRIX_PATH)
    scaler = joblib.load(SCALER_PATH)
    matrix_scaled = scaler.transform(matrix)

    cluster_count, k_report = _select_cluster_count(matrix_scaled)
    kmeans = KMeans(n_clusters=cluster_count, random_state=42, n_init=20)
    labels = kmeans.fit_predict(matrix_scaled)
    cluster_labels = _generate_cluster_labels(kmeans, scaler)

    for i, cluster_id in enumerate(labels):
        refs[i]["cluster_id"] = int(cluster_id)
        refs[i]["cluster"] = cluster_labels[int(cluster_id)]

    market_profile = _compute_market_profile(refs, cluster_count)

    with REFERENCE_DATASET_PATH.open("w", encoding="utf-8") as f:
        json.dump(refs, f, indent=2)
    joblib.dump(kmeans, KMEANS_PATH)
    with CLUSTER_LABELS_PATH.open("w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in cluster_labels.items()}, f, indent=2)
    with MARKET_PROFILE_PATH.open("w", encoding="utf-8") as f:
        json.dump(market_profile, f, indent=2)
    with K_SEARCH_REPORT_PATH.open("w", encoding="utf-8") as f:
        json.dump(k_report, f, indent=2)

    print("Trained clustering model successfully")
    print(f"Reference tracks loaded: {len(refs)}")
    print(f"Feature count: {matrix.shape[1]}")
    print(f"Cluster count: {cluster_count}")
    print(f"K search report: {K_SEARCH_REPORT_PATH}")
    for cluster_id in sorted(cluster_labels.keys()):
        print(f"  {cluster_id}: {cluster_labels[cluster_id]}")


if __name__ == "__main__":
    main()
