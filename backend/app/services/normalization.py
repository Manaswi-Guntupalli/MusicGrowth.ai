from __future__ import annotations

from .sound_dna import build_mfcc_proxies


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _scale_to_unit(value: float, min_v: float, max_v: float) -> float:
    if max_v == min_v:
        return 0.0
    return clamp01((value - min_v) / (max_v - min_v))


def normalize_features(raw: dict[str, float]) -> dict[str, float]:
    """
    Convert raw audio descriptors to Sound DNA features.

    StandardScaler is applied later by the similarity engine using scaler.pkl.
    """
    tempo = max(1.0, float(raw["tempo"]))
    loudness = float(raw["loudness_db"])
    rms_n = _scale_to_unit(float(raw["rms"]), 0.005, 0.22)
    centroid_n = _scale_to_unit(float(raw["spectral_centroid"]), 800.0, 3800.0)
    bandwidth_n = _scale_to_unit(float(raw["spectral_bandwidth"]), 700.0, 3600.0)
    zcr_n = _scale_to_unit(float(raw["zcr"]), 0.005, 0.25)
    harmonic_ratio = clamp01(float(raw["harmonic_ratio"]))
    chroma_mean = clamp01(float(raw["chroma_mean"]))
    beat_strength_n = _scale_to_unit(float(raw["beat_strength"]), 0.8, 2.6)
    tempo_consistency_n = _scale_to_unit(float(raw["tempo_consistency"]), 0.2, 0.9)

    # Requested stronger profile: energy from RMS + centroid + bandwidth.
    energy = clamp01(0.4 * rms_n + 0.3 * centroid_n + 0.3 * bandwidth_n)

    # Requested simple rhythm proxy: tempo consistency + beat strength.
    danceability = clamp01(0.55 * tempo_consistency_n + 0.45 * beat_strength_n)

    vocal_presence_n = _scale_to_unit(float(raw.get("mfcc_mean_1", -120.0)), -150.0, -40.0)
    speech_raw = 0.45 * zcr_n + 0.25 * (1.0 - harmonic_ratio) + 0.3 * vocal_presence_n
    speechiness = clamp01((speech_raw - 0.12) / 0.75)

    acoustic_base = 0.5 * (1.0 - centroid_n) + 0.3 * (1.0 - bandwidth_n) + 0.2 * harmonic_ratio
    acousticness = clamp01(acoustic_base - 0.2 * beat_strength_n - 0.15 * speechiness)

    if speechiness > 0.25:
        instrumentalness = 0.1
    else:
        instrumentalness = 0.7

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
