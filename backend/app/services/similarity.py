from __future__ import annotations

import csv
import json
import os
from functools import lru_cache
from pathlib import Path

import numpy as np

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


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


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


def top_similar(song_features: dict[str, float], top_k: int = 3) -> list[dict]:
    refs = load_reference_dataset()
    song_vec = vectorize(song_features)

    scored = []
    for ref in refs:
        ref_vec = vectorize(ref["features"])
        score = cosine_similarity(song_vec, ref_vec)
        scored.append({
            "artist": ref["artist"],
            "song": ref["song"],
            "cluster": ref["cluster"],
            "similarity": round(score * 100, 2),
            "features": ref["features"],
        })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]


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
