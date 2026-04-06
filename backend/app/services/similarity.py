from __future__ import annotations

import csv
import json
import os
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import normalize
from sklearn.preprocessing import StandardScaler

from .sound_dna import FEATURE_ORDER, build_spotify_features, safe_float, vectorize

MODEL_DIR = Path(__file__).resolve().parent.parent / "data" / "models"
REFERENCE_DATASET_PATH = MODEL_DIR / "reference_dataset.json"
MATRIX_PATH = MODEL_DIR / "sound_dna_matrix.npy"
SCALER_PATH = MODEL_DIR / "scaler.pkl"
KMEANS_PATH = MODEL_DIR / "kmeans.pkl"
CLUSTER_LABELS_PATH = MODEL_DIR / "cluster_labels.json"
MARKET_PROFILE_PATH = MODEL_DIR / "market_profile.json"
CONFIDENCE_CALIBRATION_PATH = MODEL_DIR / "confidence_calibration.json"
K_SEARCH_REPORT_PATH = MODEL_DIR / "k_search_report.json"


def _softmax(x: np.ndarray) -> np.ndarray:
    shifted = x - np.max(x)
    exp = np.exp(shifted)
    return exp / (np.sum(exp) + 1e-9)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _distance_membership(distances: np.ndarray) -> tuple[np.ndarray, float]:
    """
    Convert centroid distances into probability-like memberships.

    Uses MAD-based temperature so confidence stays stable across dense/sparse
    regions and avoids over-flattening from per-sample std spikes.
    """
    median = float(np.median(distances))
    mad = float(np.median(np.abs(distances - median))) * 1.4826
    temperature = max(mad, 0.18)
    membership = _softmax(-distances / temperature)
    return membership, temperature


def _build_reference_from_row(row: dict) -> dict | None:
    tempo_raw = safe_float(row, "tempo", 0.0)

    if tempo_raw <= 0.0:
        return None

    features = build_spotify_features(row)

    artist_name = row.get("artist_name") or row.get("artist") or "Unknown Artist"
    track_name = row.get("track_name") or row.get("song") or "Unknown Track"

    return {
        "artist": artist_name,
        "song": track_name,
        "track_id": row.get("track_id", ""),
        "cluster": "unknown",
        "features": features,
        "popularity": safe_float(row, "popularity", 0.0),
    }


def _dataset_paths() -> list[Path]:
    workspace_root = Path(__file__).resolve().parents[3]
    april_override = (os.getenv("SPOTIFY_DATASET_APRIL") or "").strip()
    nov_override = (os.getenv("SPOTIFY_DATASET_NOV") or "").strip()

    april = Path(april_override) if april_override else workspace_root / "SpotifyAudioFeaturesApril2019.csv"
    nov = Path(nov_override) if nov_override else workspace_root / "SpotifyAudioFeaturesNov2018.csv"
    return [april, nov]


def _ensure_model_dir() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)


def _compute_market_profile(refs: list[dict], cluster_count: int) -> dict[str, dict[str, float]]:
    profile: dict[str, dict[str, float]] = {}
    for cluster_id in range(cluster_count):
        rows = [r for r in refs if int(r.get("cluster_id", -1)) == cluster_id]
        saturation = len(rows)
        demand = float(np.mean([float(r.get("popularity", 0.0)) for r in rows])) if rows else 0.0
        opportunity = demand / max(1, saturation)
        profile[str(cluster_id)] = {
            "demand": round(demand, 3),
            "saturation": float(saturation),
            "opportunity_score": round(opportunity, 6),
        }
    return profile


def _compute_cluster_distance_stats(
    matrix_scaled: np.ndarray,
    kmeans: KMeans,
    cluster_to_indices: dict[int, list[int]],
) -> dict[int, dict[str, float]]:
    """
    Summarize distance distribution of each cluster for confidence calibration.
    """
    stats: dict[int, dict[str, float]] = {}
    centers = kmeans.cluster_centers_

    for cluster_id, indices in cluster_to_indices.items():
        if not indices:
            stats[int(cluster_id)] = {"p50": 0.0, "p90": 0.0}
            continue

        rows = matrix_scaled[np.array(indices, dtype=np.int32)]
        distances = np.linalg.norm(rows - centers[int(cluster_id)], axis=1)
        stats[int(cluster_id)] = {
            "p50": float(np.percentile(distances, 50)),
            "p90": float(np.percentile(distances, 90)),
        }

    return stats


def _compute_raw_margin_signals(matrix_scaled: np.ndarray, kmeans: KMeans) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute per-sample cluster labels, raw membership confidence, and margin signal.
    """
    centers = kmeans.cluster_centers_
    labels = kmeans.predict(matrix_scaled).astype(np.int32)

    raw_confidence = np.zeros(len(matrix_scaled), dtype=np.float32)
    margin_confidence = np.zeros(len(matrix_scaled), dtype=np.float32)

    for idx, row in enumerate(matrix_scaled):
        distances = np.linalg.norm(centers - row, axis=1)
        membership, _ = _distance_membership(distances)

        cluster_id = int(labels[idx])
        raw_confidence[idx] = _clamp01(float(membership[cluster_id]))

        sorted_distances = np.sort(distances)
        nearest = float(sorted_distances[0])
        second_nearest = float(sorted_distances[1]) if len(sorted_distances) > 1 else nearest
        margin_ratio = (second_nearest - nearest) / max(second_nearest, 1e-9)
        margin_confidence[idx] = _clamp01(margin_ratio * 1.6)

    return labels, raw_confidence, margin_confidence


def _compute_confidence_calibration_bins(
    matrix_scaled: np.ndarray,
    kmeans: KMeans,
    *,
    num_bins: int = 10,
    sample_size: int = 12000,
    neighbor_k: int = 25,
) -> dict[str, object]:
    """
    Build reliability bins by mapping model confidence to local cluster agreement.
    """
    if len(matrix_scaled) == 0:
        return {
            "version": 1,
            "num_bins": int(num_bins),
            "sample_size": 0,
            "neighbor_k": int(neighbor_k),
            "global_agreement": 0.0,
            "bins": [],
        }

    labels, raw_conf, margin_conf = _compute_raw_margin_signals(matrix_scaled, kmeans)
    pre_calibration = np.clip((0.7 * raw_conf) + (0.3 * margin_conf), 0.0, 1.0)

    rng = np.random.RandomState(42)
    all_indices = np.arange(len(matrix_scaled))
    if len(all_indices) > sample_size:
        sampled_indices = rng.choice(all_indices, size=sample_size, replace=False)
    else:
        sampled_indices = all_indices

    n_neighbors = min(max(3, neighbor_k + 1), len(matrix_scaled))
    neighbors = NearestNeighbors(n_neighbors=n_neighbors, metric="euclidean")
    neighbors.fit(matrix_scaled)
    _, neighbor_indices = neighbors.kneighbors(matrix_scaled[sampled_indices], return_distance=True)

    if n_neighbors > 1:
        neighbor_labels = labels[neighbor_indices[:, 1:]]
        agreement = np.mean(neighbor_labels == labels[sampled_indices, None], axis=1)
    else:
        agreement = np.ones(len(sampled_indices), dtype=np.float32)

    scores = pre_calibration[sampled_indices]
    edges = np.linspace(0.0, 1.0, num_bins + 1)

    prior = float(np.mean(agreement)) if len(agreement) else 0.5
    bins: list[dict[str, float | int]] = []
    previous_calibrated = 0.0

    for i in range(num_bins):
        lower = float(edges[i])
        upper = float(edges[i + 1])

        if i < num_bins - 1:
            mask = (scores >= lower) & (scores < upper)
        else:
            mask = (scores >= lower) & (scores <= upper)

        count = int(np.sum(mask))
        if count > 0:
            empirical = float(np.mean(agreement[mask]))
            calibrated = (empirical * count + prior * 25.0) / (count + 25.0)
        else:
            calibrated = previous_calibrated

        calibrated = _clamp01(max(calibrated, previous_calibrated))
        previous_calibrated = calibrated

        bins.append(
            {
                "lower": round(lower, 6),
                "upper": round(upper, 6),
                "count": count,
                "calibrated": round(float(calibrated), 6),
            }
        )

    return {
        "version": 1,
        "num_bins": int(num_bins),
        "sample_size": int(len(sampled_indices)),
        "neighbor_k": int(max(1, n_neighbors - 1)),
        "global_agreement": round(prior, 6),
        "bins": bins,
    }


def _apply_confidence_calibration(score: float, calibration: dict[str, object] | None) -> float:
    if not calibration:
        return _clamp01(score)

    bins = calibration.get("bins") if isinstance(calibration, dict) else None
    if not isinstance(bins, list) or not bins:
        return _clamp01(score)

    s = _clamp01(score)
    for entry in bins:
        try:
            upper = float(entry.get("upper", 1.0))
            calibrated = float(entry.get("calibrated", s))
        except (TypeError, ValueError, AttributeError):
            continue

        if s <= upper:
            return _clamp01(calibrated)

    try:
        return _clamp01(float(bins[-1].get("calibrated", s)))
    except (TypeError, ValueError, AttributeError):
        return _clamp01(s)


def _label_from_centroid(centroid: dict[str, float]) -> str:
    if centroid["energy"] > 0.74 and centroid["danceability"] > 0.68:
        return "High Energy Pop"
    if centroid["acousticness"] > 0.67 and centroid["energy"] < 0.46:
        return "Acoustic Emotional"
    if centroid["instrumentalness"] > 0.55 and centroid["speechiness"] < 0.2:
        return "Lo-fi Indie"
    if centroid["valence"] < 0.36 and centroid["energy"] < 0.52:
        return "Moody Alternative"
    if centroid["speechiness"] > 0.3:
        return "Rhythmic Vocal Forward"
    return "Balanced Indie"


def _cluster_descriptor(centroid: dict[str, float]) -> str:
    descriptors: list[str] = []

    if centroid["tempo"] >= 140:
        descriptors.append("Fast Tempo")
    elif centroid["tempo"] <= 95:
        descriptors.append("Slow Burn")
    else:
        descriptors.append("Mid Tempo")

    if centroid["acousticness"] >= 0.6:
        descriptors.append("Organic")
    elif centroid["instrumentalness"] >= 0.45:
        descriptors.append("Instrumental")
    else:
        descriptors.append("Synth Tilt")

    if centroid["valence"] >= 0.6:
        descriptors.append("Bright")
    elif centroid["valence"] <= 0.35:
        descriptors.append("Moody")
    else:
        descriptors.append("Neutral")

    return " / ".join(descriptors)


def _generate_cluster_labels(kmeans: KMeans, scaler: StandardScaler) -> dict[int, str]:
    centers_unscaled = scaler.inverse_transform(kmeans.cluster_centers_)
    labels: dict[int, str] = {}
    used_names: set[str] = set()

    for i, center in enumerate(centers_unscaled):
        centroid = {FEATURE_ORDER[idx]: float(center[idx]) for idx in range(len(FEATURE_ORDER))}
        base = _label_from_centroid(centroid)
        descriptor = _cluster_descriptor(centroid)
        candidate = f"{base} - {descriptor}"

        if candidate in used_names:
            candidate = f"{base} - {descriptor} - C{i}"

        used_names.add(candidate)
        labels[i] = candidate

    return labels


def _fit_and_persist_models(refs: list[dict]) -> dict:
    if not refs:
        raise ValueError("Reference dataset is empty; cannot build models.")

    matrix = np.vstack([np.array(vectorize(ref["features"]), dtype=np.float32) for ref in refs])

    scaler = StandardScaler()
    matrix_scaled = scaler.fit_transform(matrix)

    cluster_count = int(os.getenv("STYLE_CLUSTER_COUNT", "10"))
    cluster_count = max(8, min(cluster_count, 12))
    kmeans = KMeans(n_clusters=cluster_count, random_state=42, n_init=20)
    labels = kmeans.fit_predict(matrix_scaled)

    cluster_labels = _generate_cluster_labels(kmeans, scaler)

    for i, cluster_id in enumerate(labels):
        refs[i]["cluster_id"] = int(cluster_id)
        refs[i]["cluster"] = cluster_labels[int(cluster_id)]

    market_profile = _compute_market_profile(refs, cluster_count)

    _ensure_model_dir()
    np.save(MATRIX_PATH, matrix)
    with REFERENCE_DATASET_PATH.open("w", encoding="utf-8") as f:
        json.dump(refs, f, indent=2)
    joblib.dump(scaler, SCALER_PATH)
    joblib.dump(kmeans, KMEANS_PATH)
    with CLUSTER_LABELS_PATH.open("w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in cluster_labels.items()}, f, indent=2)
    with MARKET_PROFILE_PATH.open("w", encoding="utf-8") as f:
        json.dump(market_profile, f, indent=2)

    return {
        "refs": refs,
        "matrix": matrix,
        "scaler": scaler,
        "kmeans": kmeans,
        "cluster_labels": cluster_labels,
        "market_profile": market_profile,
    }


@lru_cache(maxsize=1)
def load_reference_dataset() -> list[dict]:
    if REFERENCE_DATASET_PATH.exists():
        with REFERENCE_DATASET_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)

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
    return np.array([float(features[name]) for name in FEATURE_ORDER], dtype=np.float32)


@lru_cache(maxsize=1)
def get_similarity_model() -> dict:
    refs = load_reference_dataset()

    if SCALER_PATH.exists() and KMEANS_PATH.exists() and MATRIX_PATH.exists():
        matrix = np.load(MATRIX_PATH)
        scaler: StandardScaler = joblib.load(SCALER_PATH)
        kmeans: KMeans = joblib.load(KMEANS_PATH)

        if CLUSTER_LABELS_PATH.exists():
            with CLUSTER_LABELS_PATH.open("r", encoding="utf-8") as f:
                cluster_labels = {int(k): str(v) for k, v in json.load(f).items()}
        else:
            cluster_labels = _generate_cluster_labels(kmeans, scaler)

        if MARKET_PROFILE_PATH.exists():
            with MARKET_PROFILE_PATH.open("r", encoding="utf-8") as f:
                market_profile = json.load(f)
        else:
            market_profile = _compute_market_profile(refs, int(kmeans.n_clusters))
    else:
        trained = _fit_and_persist_models(refs)
        matrix = trained["matrix"]
        scaler = trained["scaler"]
        kmeans = trained["kmeans"]
        cluster_labels = trained["cluster_labels"]
        market_profile = trained["market_profile"]
        refs = trained["refs"]

    matrix_scaled = scaler.transform(matrix)
    matrix_normalized = normalize(matrix_scaled)
    if not refs:
        raise ValueError("Reference dataset is empty; cannot run similarity model.")

    cluster_to_indices: dict[int, list[int]] = {int(i): [] for i in range(int(kmeans.n_clusters))}
    for idx, ref in enumerate(refs):
        cluster_id = int(ref.get("cluster_id", -1))
        if cluster_id < 0:
            cluster_id = int(kmeans.predict(matrix_scaled[idx].reshape(1, -1))[0])
            ref["cluster_id"] = cluster_id
            ref["cluster"] = cluster_labels.get(cluster_id, f"Cluster {cluster_id}")
        cluster_to_indices.setdefault(cluster_id, []).append(idx)

    cluster_distance_stats = _compute_cluster_distance_stats(matrix_scaled, kmeans, cluster_to_indices)

    if CONFIDENCE_CALIBRATION_PATH.exists():
        try:
            with CONFIDENCE_CALIBRATION_PATH.open("r", encoding="utf-8") as f:
                confidence_calibration = json.load(f)
        except Exception:
            confidence_calibration = _compute_confidence_calibration_bins(matrix_scaled, kmeans)
    else:
        confidence_calibration = _compute_confidence_calibration_bins(matrix_scaled, kmeans)

    try:
        with CONFIDENCE_CALIBRATION_PATH.open("w", encoding="utf-8") as f:
            json.dump(confidence_calibration, f, indent=2)
    except OSError:
        pass

    center_spread = np.std(kmeans.cluster_centers_, axis=0)
    spread_sum = float(np.sum(center_spread) + 1e-9)
    feature_importance = {
        FEATURE_ORDER[i]: float(center_spread[i] / spread_sum)
        for i in range(len(FEATURE_ORDER))
    }

    return {
        "refs": refs,
        "matrix": matrix,
        "matrix_scaled": matrix_scaled,
        "matrix_normalized": matrix_normalized,
        "scaler": scaler,
        "kmeans": kmeans,
        "cluster_labels": cluster_labels,
        "cluster_to_indices": cluster_to_indices,
        "cluster_distance_stats": cluster_distance_stats,
        "confidence_calibration": confidence_calibration,
        "feature_importance": feature_importance,
        "market_profile": market_profile,
    }


def top_similar(song_features: dict[str, float], cluster_id: int | None = None, top_k: int = 3) -> list[dict]:
    model = get_similarity_model()
    refs = model["refs"]
    scaler: StandardScaler = model["scaler"]
    matrix_normalized: np.ndarray = model["matrix_normalized"]
    cluster_to_indices: dict[int, list[int]] = model["cluster_to_indices"]
    kmeans: KMeans = model["kmeans"]

    if not refs:
        return []

    query = vectorize(song_features).reshape(1, -1)
    query_scaled = scaler.transform(query)
    query_normalized = normalize(query_scaled)

    if cluster_id is None:
        cluster_id = int(kmeans.predict(query_scaled)[0])

    scoped_indices = cluster_to_indices.get(cluster_id, [])
    if not scoped_indices:
        scoped_indices = list(range(len(refs)))

    scoped_matrix = matrix_normalized[scoped_indices]
    scores = cosine_similarity(query_normalized, scoped_matrix)[0]
    sorted_local = np.argsort(scores)[::-1]
    neighbors = min(top_k, len(sorted_local))

    results: list[dict] = []
    for local_idx in sorted_local[:neighbors]:
        global_idx = int(scoped_indices[int(local_idx)])
        ref = refs[global_idx]
        similarity_score = float((scores[int(local_idx)] + 1.0) * 50.0)
        results.append(
            {
                "artist": ref["artist"],
                "song": ref["song"],
                "cluster": ref["cluster"],
                "similarity": round(max(0.0, min(100.0, similarity_score)), 2),
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
    confidence_calibration: dict[str, object] | None = model.get("confidence_calibration")

    query = vectorize(song_features).reshape(1, -1)
    query_scaled = scaler.transform(query)
    cluster_id = int(kmeans.predict(query_scaled)[0])

    distances = np.linalg.norm(kmeans.cluster_centers_ - query_scaled[0], axis=1)

    membership, _ = _distance_membership(distances)
    raw_confidence = _clamp01(float(membership[cluster_id]))

    sorted_distances = np.sort(distances)
    nearest = float(sorted_distances[0])
    if len(sorted_distances) > 1:
        second_nearest = float(sorted_distances[1])
        margin_ratio = (second_nearest - nearest) / max(second_nearest, 1e-9)
    else:
        margin_ratio = 0.0
    margin_confidence = _clamp01(margin_ratio * 1.6)

    distance_stats = cluster_distance_stats.get(cluster_id, {"p50": nearest, "p90": nearest + 1e-6})
    p50 = max(float(distance_stats.get("p50", nearest)), 1e-6)
    p90 = max(float(distance_stats.get("p90", p50 + 1e-6)), p50 + 1e-6)
    spread = max(p90 - p50, 1e-6)
    compactness = float(1.0 / (1.0 + np.exp((nearest - p50) / (spread * 1.2))))

    # Use reliability bins learned from neighborhood agreement for calibrated confidence.
    pre_calibration = _clamp01((0.7 * raw_confidence) + (0.3 * margin_confidence))
    calibrated = _apply_confidence_calibration(pre_calibration, confidence_calibration)
    confidence = _clamp01((0.85 * calibrated) + (0.15 * compactness))

    return {
        "cluster_id": cluster_id,
        "label": cluster_labels.get(cluster_id, f"Cluster {cluster_id}"),
        "confidence": round(confidence * 100.0, 2),
        "raw_confidence": round(raw_confidence * 100.0, 2),
    }


def cluster_membership_probabilities(song_features: dict[str, float]) -> dict[int, float]:
    model = get_similarity_model()
    scaler: StandardScaler = model["scaler"]
    kmeans: KMeans = model["kmeans"]

    query = vectorize(song_features).reshape(1, -1)
    query_scaled = scaler.transform(query)

    distances = np.linalg.norm(kmeans.cluster_centers_ - query_scaled[0], axis=1)
    membership, _ = _distance_membership(distances)

    return {int(i): float(membership[i]) for i in range(len(membership))}


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


def feature_importance_for_song(song_features: dict[str, float], cluster_id: int) -> dict[str, float]:
    model = get_similarity_model()
    scaler: StandardScaler = model["scaler"]
    kmeans: KMeans = model["kmeans"]
    base_importance: dict[str, float] = model["feature_importance"]

    query = vectorize(song_features).reshape(1, -1)
    query_scaled = scaler.transform(query)[0]
    centroid = kmeans.cluster_centers_[cluster_id]
    contributions = np.abs(query_scaled - centroid)

    weighted = {
        FEATURE_ORDER[i]: float(contributions[i]) * float(base_importance[FEATURE_ORDER[i]])
        for i in range(len(FEATURE_ORDER))
    }
    total = sum(weighted.values()) + 1e-9
    return {k: v / total for k, v in weighted.items()}


def get_market_profile() -> dict[str, dict[str, float]]:
    model = get_similarity_model()
    return model["market_profile"]
