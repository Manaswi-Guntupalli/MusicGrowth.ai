from __future__ import annotations

from typing import Final

FEATURE_ORDER: Final[list[str]] = [
    "tempo",
    "energy",
    "danceability",
    "valence",
    "acousticness",
    "instrumentalness",
    "liveness",
    "speechiness",
    "loudness",
    "mfcc_mean_1",
    "mfcc_mean_2",
    "mfcc_mean_3",
    "mfcc_mean_4",
    "mfcc_mean_5",
]

CORE_FEATURES: Final[list[str]] = [
    "tempo",
    "energy",
    "danceability",
    "valence",
    "acousticness",
    "instrumentalness",
    "liveness",
    "speechiness",
    "loudness",
]


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def safe_float(row: dict, key: str, fallback: float = 0.0) -> float:
    try:
        return float(row.get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def build_mfcc_proxies(base: dict[str, float]) -> dict[str, float]:
    """
    Build deterministic MFCC-like channels when true MFCCs are unavailable.

    Spotify tabular datasets do not contain MFCC columns, so this creates stable
    timbre proxies to keep feature dimensionality consistent with live audio.
    """
    tempo = base["tempo"]
    energy = base["energy"]
    danceability = base["danceability"]
    valence = base["valence"]
    acousticness = base["acousticness"]
    instrumentalness = base["instrumentalness"]
    liveness = base["liveness"]
    speechiness = base["speechiness"]
    loudness = base["loudness"]

    return {
        "mfcc_mean_1": 1.15 * loudness + 0.04 * tempo - 18.0,
        "mfcc_mean_2": 110.0 * (acousticness - energy) + 45.0 * (instrumentalness - speechiness),
        "mfcc_mean_3": 95.0 * (valence - 0.5) + 30.0 * (danceability - liveness),
        "mfcc_mean_4": 105.0 * (speechiness - 0.1) + 25.0 * (1.0 - acousticness),
        "mfcc_mean_5": 85.0 * (instrumentalness - 0.3) - 55.0 * (danceability - 0.5),
    }


def vectorize(features: dict[str, float]) -> list[float]:
    return [float(features[name]) for name in FEATURE_ORDER]


def build_spotify_features(row: dict) -> dict[str, float]:
    base = {
        "tempo": max(1.0, safe_float(row, "tempo", 120.0)),
        "energy": clamp01(safe_float(row, "energy", 0.0)),
        "danceability": clamp01(safe_float(row, "danceability", 0.0)),
        "valence": clamp01(safe_float(row, "valence", 0.0)),
        "acousticness": clamp01(safe_float(row, "acousticness", 0.0)),
        "instrumentalness": clamp01(safe_float(row, "instrumentalness", 0.0)),
        "liveness": clamp01(safe_float(row, "liveness", 0.0)),
        "speechiness": clamp01(safe_float(row, "speechiness", 0.0)),
        "loudness": safe_float(row, "loudness", -15.0),
    }
    base.update(build_mfcc_proxies(base))
    return base
