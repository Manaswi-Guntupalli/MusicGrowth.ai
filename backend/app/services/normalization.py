from __future__ import annotations

from typing import Any

from .sound_dna import build_mfcc_proxies


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _scale_to_unit(value: float, min_v: float, max_v: float) -> float:
    if max_v == min_v:
        return 0.0
    return clamp01((value - min_v) / (max_v - min_v))


def _resolve_scale_bounds(raw: dict[str, Any], feature: str, default_min: float, default_max: float) -> tuple[float, float]:
    """
    Resolve scaling bounds from payload-provided dataset stats when available.

    Supports either:
    - raw["scale_bounds"][feature] = {"min": ..., "max": ...}
    - raw[f"{feature}_min"] / raw[f"{feature}_max"]
    """
    bounds = raw.get("scale_bounds")
    if isinstance(bounds, dict):
        feature_bounds = bounds.get(feature)
        if isinstance(feature_bounds, dict):
            min_v = feature_bounds.get("min", default_min)
            max_v = feature_bounds.get("max", default_max)
            try:
                min_f = float(min_v)
                max_f = float(max_v)
                if max_f > min_f:
                    return min_f, max_f
            except (TypeError, ValueError):
                pass

    min_key = f"{feature}_min"
    max_key = f"{feature}_max"
    if min_key in raw and max_key in raw:
        try:
            min_f = float(raw[min_key])
            max_f = float(raw[max_key])
            if max_f > min_f:
                return min_f, max_f
        except (TypeError, ValueError):
            pass

    return default_min, default_max


def normalize_features(raw: dict[str, Any]) -> dict[str, float]:
    """
    Convert raw audio descriptors to Sound DNA features.

    StandardScaler is applied later by the similarity engine using scaler.pkl.
    """
    tempo = max(1.0, float(raw["tempo"]))
    loudness = float(raw["loudness_db"])
    rms_min, rms_max = _resolve_scale_bounds(raw, "rms", 0.005, 0.22)
    centroid_min, centroid_max = _resolve_scale_bounds(raw, "spectral_centroid", 800.0, 3800.0)
    bandwidth_min, bandwidth_max = _resolve_scale_bounds(raw, "spectral_bandwidth", 700.0, 3600.0)
    zcr_min, zcr_max = _resolve_scale_bounds(raw, "zcr", 0.005, 0.25)
    beat_min, beat_max = _resolve_scale_bounds(raw, "beat_strength", 0.8, 2.6)
    consistency_min, consistency_max = _resolve_scale_bounds(raw, "tempo_consistency", 0.2, 0.9)

    rms_n = _scale_to_unit(float(raw["rms"]), rms_min, rms_max)
    centroid_n = _scale_to_unit(float(raw["spectral_centroid"]), centroid_min, centroid_max)
    bandwidth_n = _scale_to_unit(float(raw["spectral_bandwidth"]), bandwidth_min, bandwidth_max)
    zcr_n = _scale_to_unit(float(raw["zcr"]), zcr_min, zcr_max)
    harmonic_ratio = clamp01(float(raw["harmonic_ratio"]))
    chroma_mean = clamp01(float(raw["chroma_mean"]))
    beat_strength_n = _scale_to_unit(float(raw["beat_strength"]), beat_min, beat_max)
    tempo_consistency_n = _scale_to_unit(float(raw["tempo_consistency"]), consistency_min, consistency_max)

    # Slight RMS-forward tuning keeps perceived intensity closer to loudness dynamics.
    energy = clamp01(0.5 * rms_n + 0.25 * centroid_n + 0.25 * bandwidth_n)

    # Requested simple rhythm proxy: tempo consistency + beat strength.
    danceability = clamp01(0.55 * tempo_consistency_n + 0.45 * beat_strength_n)

    vocal_presence_n = _scale_to_unit(float(raw.get("mfcc_mean_1", -120.0)), -150.0, -40.0)
    speech_raw = 0.45 * zcr_n + 0.25 * (1.0 - harmonic_ratio) + 0.3 * vocal_presence_n
    speechiness = clamp01((speech_raw - 0.12) / 0.75)

    acoustic_base = 0.5 * (1.0 - centroid_n) + 0.3 * (1.0 - bandwidth_n) + 0.2 * harmonic_ratio
    acousticness = clamp01(acoustic_base - 0.2 * beat_strength_n - 0.15 * speechiness)

    instrumentalness = clamp01(1.0 - speechiness)

    valence = clamp01(0.48 * centroid_n + 0.32 * chroma_mean + 0.2 * _scale_to_unit(tempo, 60.0, 180.0))
    liveness = clamp01(0.55 * beat_strength_n + 0.45 * zcr_n)

    features = {
        "tempo": tempo,
        "energy": energy,
        "danceability": danceability,
        "valence": valence,
        "acousticness": acousticness,
        "instrumentalness": instrumentalness,
        "liveness": liveness,
        "speechiness": speechiness,
        "loudness": loudness,
    }

    proxy_mfcc = build_mfcc_proxies(features)
    for i in range(1, 6):
        actual = float(raw[f"mfcc_mean_{i}"])
        proxy = float(proxy_mfcc[f"mfcc_mean_{i}"])
        # Blend true MFCC with proxy so live audio and Spotify-tabular references share a stable space.
        features[f"mfcc_mean_{i}"] = 0.7 * actual + 0.3 * proxy

    return features
