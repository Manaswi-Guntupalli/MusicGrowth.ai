from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.cluster import KMeans

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.similarity import (
    CLUSTER_LABELS_PATH,
    KMEANS_PATH,
    MARKET_PROFILE_PATH,
    MATRIX_PATH,
    REFERENCE_DATASET_PATH,
    SCALER_PATH,
    _compute_market_profile,
    _generate_cluster_labels,
)


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

    cluster_count = int(os.getenv("STYLE_CLUSTER_COUNT", "10"))
    cluster_count = max(8, min(cluster_count, 12))
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

    print("Trained clustering model successfully")
    print(f"Reference tracks loaded: {len(refs)}")
    print(f"Feature count: {matrix.shape[1]}")
    print(f"Cluster count: {cluster_count}")
    for cluster_id in sorted(cluster_labels.keys()):
        print(f"  {cluster_id}: {cluster_labels[cluster_id]}")


if __name__ == "__main__":
    main()
