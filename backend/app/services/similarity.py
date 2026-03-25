from __future__ import annotations

import csv
import json
import os
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from .normalization import clamp01, minmax

FEATURE_ORDER = [
    "tempo",
    "energy",
    "danceability",
    "valence",
    "acousticness",
    "instrumentalness",
    "speechiness",
    "loudness",
    "liveness",
]


def _distance_to_similarity(distance: float) -> float:
    # Cosine distance is 0 (identical) to 2 (opposite). Convert to 0-100 score.
    similarity = (1.0 - (distance / 2.0)) * 100.0
    return max(0.0, min(100.0, similarity))


def _softmax(x: np.ndarray) -> np.ndarray:
    shifted = x - np.max(x)
    exp = np.exp(shifted)
    return exp / (np.sum(exp) + 1e-9)


def _label_from_centroid(features: dict[str, float]) -> str:
    if features["energy"] > 0.75 and features["danceability"] > 0.7:
        return "High-Energy Mainstream"
    if features["acousticness"] > 0.7 and features["energy"] < 0.45:
        return "Acoustic Chill"
    if features["instrumentalness"] > 0.55 and features["speechiness"] < 0.25:
        return "Instrumental Atmospheric"
    if features["valence"] > 0.65:
        return "Bright Upbeat"
    if features["valence"] < 0.35 and features["energy"] < 0.5:
        return "Moody Introspective"
    return "Balanced Indie"


def _infer_cluster(features: dict[str, float]) -> str:
    if features["energy"] > 0.72 and features["danceability"] > 0.68:
        return "mainstream-pop"
    if features["acousticness"] > 0.65 and features["energy"] < 0.45:
        return "chill-acoustic"
    if features["energy"] > 0.78 and features["acousticness"] < 0.3:
        return "electronic-dance"
    if features["acousticness"] > 0.55 and features["danceability"] < 0.6:
        return "indie-bedroom"
    return "experimental-alt"


def _safe_float(row: dict, key: str, fallback: float = 0.0) -> float:
    try:
        return float(row.get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def _build_reference_from_row(row: dict) -> dict | None:
    tempo_raw = _safe_float(row, "tempo", 0.0)
    loudness_raw = _safe_float(row, "loudness", -40.0)

    if tempo_raw <= 0.0:
        return None

    features = {
        "tempo": minmax("tempo", tempo_raw),
        "energy": clamp01(_safe_float(row, "energy", 0.0)),
        "danceability": clamp01(_safe_float(row, "danceability", 0.0)),
        "valence": clamp01(_safe_float(row, "valence", 0.0)),
        "acousticness": clamp01(_safe_float(row, "acousticness", 0.0)),
        "instrumentalness": clamp01(_safe_float(row, "instrumentalness", 0.0)),
        "speechiness": clamp01(_safe_float(row, "speechiness", 0.0)),
        "loudness": minmax("loudness_db", loudness_raw),
        "liveness": clamp01(_safe_float(row, "liveness", 0.0)),
    }

    return {
        "artist": row.get("artist_name", "Unknown Artist"),
        "song": row.get("track_name", "Unknown Track"),
        "track_id": row.get("track_id", ""),
        "cluster": _infer_cluster(features),
        "features": features,
        "popularity": _safe_float(row, "popularity", 0.0),
    }


def _dataset_paths() -> list[Path]:
    workspace_root = Path(__file__).resolve().parents[3]
    april = Path(os.getenv("SPOTIFY_DATASET_APRIL", workspace_root / "SpotifyAudioFeaturesApril2019.csv"))
    nov = Path(os.getenv("SPOTIFY_DATASET_NOV", workspace_root / "SpotifyAudioFeaturesNov2018.csv"))
    return [april, nov]


@lru_cache(maxsize=1)
def load_reference_dataset() -> list[dict]:
    min_popularity = float(os.getenv("SPOTIFY_MIN_POPULARITY", "35"))
    seen_track_ids: set[str] = set()
    refs: list[dict] = []

    for path in _dataset_paths():
        if not path.exists():
            continue

        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entry = _build_reference_from_row(row)
                if entry is None:
                    continue

                track_id = entry["track_id"]
                if track_id and track_id in seen_track_ids:
                    continue
                if entry["popularity"] < min_popularity:
                    continue

                if track_id:
                    seen_track_ids.add(track_id)
                refs.append(entry)

    if refs:
        return refs

    # Fallback keeps app usable if CSV files are missing.
    fallback = Path(__file__).resolve().parent.parent / "data" / "reference_dataset.json"
    with fallback.open("r", encoding="utf-8") as f:
        return json.load(f)


def vectorize(features: dict[str, float]) -> np.ndarray:
    return np.array([features[name] for name in FEATURE_ORDER], dtype=np.float32)


@lru_cache(maxsize=1)
def get_similarity_model() -> dict:
    refs = load_reference_dataset()
    if not refs:
        raise ValueError("Reference dataset is empty; cannot train similarity model.")

    matrix = np.vstack([vectorize(ref["features"]) for ref in refs])
    scaler = StandardScaler()
    matrix_scaled = scaler.fit_transform(matrix)

    nn = NearestNeighbors(metric="cosine", algorithm="brute")
    nn.fit(matrix_scaled)

    cluster_count = int(os.getenv("STYLE_CLUSTER_COUNT", "8"))
    cluster_count = max(3, min(cluster_count, 16))
    kmeans = KMeans(n_clusters=cluster_count, random_state=42, n_init=10)
    kmeans.fit(matrix_scaled)

    # Cluster compactness stats for confidence calibration.
    labels = kmeans.labels_
    dist_to_assigned = np.linalg.norm(matrix_scaled - kmeans.cluster_centers_[labels], axis=1)
    cluster_distance_stats: dict[int, dict[str, float]] = {}
    for cluster_id in range(cluster_count):
        cluster_dist = dist_to_assigned[labels == cluster_id]
        if len(cluster_dist) == 0:
            cluster_distance_stats[cluster_id] = {"mean": 1.0, "std": 0.25}
            continue
        cluster_distance_stats[cluster_id] = {
            "mean": float(np.mean(cluster_dist)),
            "std": float(np.std(cluster_dist) + 1e-6),
        }

    centers_unscaled = scaler.inverse_transform(kmeans.cluster_centers_)
    cluster_labels: dict[int, str] = {}
    for i, center in enumerate(centers_unscaled):
        center_features = {FEATURE_ORDER[idx]: float(center[idx]) for idx in range(len(FEATURE_ORDER))}
        cluster_labels[i] = _label_from_centroid(center_features)

    return {
        "refs": refs,
        "scaler": scaler,
        "nn": nn,
        "kmeans": kmeans,
        "cluster_labels": cluster_labels,
        "cluster_distance_stats": cluster_distance_stats,
    }


def top_similar(song_features: dict[str, float], top_k: int = 3) -> list[dict]:
    model = get_similarity_model()
    refs = model["refs"]
    scaler: StandardScaler = model["scaler"]
    nn: NearestNeighbors = model["nn"]

    if not refs:
        return []

    query = vectorize(song_features).reshape(1, -1)
    query_scaled = scaler.transform(query)
    neighbors = min(top_k, len(refs))
    distances, indices = nn.kneighbors(query_scaled, n_neighbors=neighbors)

    results: list[dict] = []
    for distance, idx in zip(distances[0], indices[0]):
        ref = refs[int(idx)]
        results.append(
            {
                "artist": ref["artist"],
                "song": ref["song"],
                "cluster": ref["cluster"],
                "similarity": round(_distance_to_similarity(float(distance)), 2),
                "features": ref["features"],
            }
        )

    return results


def predict_style_cluster(song_features: dict[str, float]) -> dict:
    model = get_similarity_model()
    scaler: StandardScaler = model["scaler"]
    kmeans: KMeans = model["kmeans"]
    cluster_labels: dict[int, str] = model["cluster_labels"]
    cluster_distance_stats: dict[int, dict[str, float]] = model["cluster_distance_stats"]

    query = vectorize(song_features).reshape(1, -1)
    query_scaled = scaler.transform(query)
    cluster_id = int(kmeans.predict(query_scaled)[0])

    distances = np.linalg.norm(kmeans.cluster_centers_ - query_scaled[0], axis=1)

    # Soft assignment gives probability-like membership confidence across clusters.
    temperature = max(float(np.std(distances)), 0.35)
    membership = _softmax(-distances / temperature)
    membership_conf = float(membership[cluster_id])

    # Compactness calibrates confidence against typical in-cluster training distances.
    nearest = float(distances[cluster_id])
    stats = cluster_distance_stats.get(cluster_id, {"mean": 1.0, "std": 0.25})
    z = (nearest - stats["mean"]) / (stats["std"] + 1e-6)
    compactness_conf = float(1.0 / (1.0 + np.exp(z)))

    confidence = 0.7 * membership_conf + 0.3 * compactness_conf
    confidence = max(0.0, min(1.0, confidence))

    return {
        "cluster_id": cluster_id,
        "label": cluster_labels.get(cluster_id, "Balanced Indie"),
        "confidence": round(confidence * 100.0, 2),
    }


def reference_mean(top_refs: list[dict]) -> dict[str, float]:
    agg: dict[str, float] = {name: 0.0 for name in FEATURE_ORDER}
    if not top_refs:
        return agg

    for ref in top_refs:
        for name in FEATURE_ORDER:
            agg[name] += ref["features"][name]

    for name in FEATURE_ORDER:
        agg[name] /= len(top_refs)
    return agg
