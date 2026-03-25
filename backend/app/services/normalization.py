from __future__ import annotations

from typing import Final

MIN_MAX: Final[dict[str, tuple[float, float]]] = {
    "tempo": (50.0, 180.0),
    "loudness_db": (-40.0, 0.0),
    "spectral_centroid": (500.0, 6000.0),
    "spectral_bandwidth": (500.0, 5000.0),
    "zcr": (0.01, 0.25),
    "rms": (0.01, 0.5),
    "onset_strength": (0.0, 5.0),
    "harmonic_ratio": (0.1, 0.95),
    "chroma_mean": (0.0, 1.0),
    "mfcc_mean": (-200.0, 100.0),
}


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def minmax(feature_name: str, value: float) -> float:
    min_v, max_v = MIN_MAX[feature_name]
    if max_v == min_v:
        return 0.0
    return clamp01((value - min_v) / (max_v - min_v))


def normalize_features(raw: dict[str, float]) -> dict[str, float]:
    tempo_n = minmax("tempo", raw["tempo"])
    loudness_n = minmax("loudness_db", raw["loudness_db"])
    rms_n = minmax("rms", raw["rms"])
    onset_n = minmax("onset_strength", raw["onset_strength"])
    centroid_n = minmax("spectral_centroid", raw["spectral_centroid"])
    bandwidth_n = minmax("spectral_bandwidth", raw["spectral_bandwidth"])
    zcr_n = minmax("zcr", raw["zcr"])
    harmonic_ratio_n = minmax("harmonic_ratio", raw["harmonic_ratio"])

    energy = clamp01(rms_n * 0.5 + loudness_n * 0.3 + onset_n * 0.2)
    danceability = clamp01(tempo_n * 0.35 + onset_n * 0.35 + (1.0 - zcr_n) * 0.3)
    acousticness = clamp01(harmonic_ratio_n * 0.55 + (1.0 - bandwidth_n) * 0.45)
    speechiness = clamp01(zcr_n * 0.5 + (1.0 - harmonic_ratio_n) * 0.5)
    instrumentalness = clamp01(harmonic_ratio_n * 0.45 + (1.0 - speechiness) * 0.55)
    valence = clamp01(centroid_n * 0.55 + tempo_n * 0.25 + raw["chroma_mean"] * 0.2)
    liveness = clamp01(raw["onset_strength"] / 7.0 + raw["zcr"])

    return {
        "tempo": tempo_n,
        "energy": energy,
        "danceability": danceability,
        "valence": valence,
        "acousticness": acousticness,
        "instrumentalness": instrumentalness,
        "speechiness": speechiness,
        "loudness": loudness_n,
        "liveness": liveness,
        "spectral_centroid": centroid_n,
        "spectral_bandwidth": bandwidth_n,
        "zcr": zcr_n,
    }
