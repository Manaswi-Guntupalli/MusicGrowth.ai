from __future__ import annotations

from .feature_extraction import extract_features_from_path
from .interpretation import mood_label, production_style
from .normalization import normalize_features
from .similarity import reference_mean, top_similar
from .strategy import build_differences, build_market_gaps, build_paths


def run_analysis(audio_path: str, segment_mode: str = "best") -> dict:
    raw = extract_features_from_path(audio_path, segment_mode=segment_mode)
    normalized = normalize_features(raw)

    top_refs = top_similar(normalized, top_k=3)
    ref_avg = reference_mean(top_refs)
    differences = build_differences(normalized, ref_avg)

    sound_dna = {
        "tempo": round(raw["tempo"], 2),
        "energy": round(normalized["energy"], 3),
        "danceability": round(normalized["danceability"], 3),
        "valence": round(normalized["valence"], 3),
        "acousticness": round(normalized["acousticness"], 3),
        "instrumentalness": round(normalized["instrumentalness"], 3),
        "speechiness": round(normalized["speechiness"], 3),
        "loudness": round(normalized["loudness"], 3),
        "liveness": round(normalized["liveness"], 3),
        "spectral_centroid": round(normalized["spectral_centroid"], 3),
        "spectral_bandwidth": round(normalized["spectral_bandwidth"], 3),
        "zcr": round(normalized["zcr"], 3),
        "production_style": production_style(normalized),
        "mood": mood_label(normalized),
    }

    return {
        "sound_dna": sound_dna,
        "top_similar": [
            {
                "artist": ref["artist"],
                "song": ref["song"],
                "cluster": ref["cluster"],
                "similarity": ref["similarity"],
            }
            for ref in top_refs
        ],
        "differences": differences,
        "market_gaps": build_market_gaps(normalized),
        "paths": build_paths(),
    }
