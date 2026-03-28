from __future__ import annotations

from .feature_extraction import extract_features_from_path
from .interpretation import mood_label, production_style
from .normalization import normalize_features
from .similarity import (
    feature_importance_for_song,
    get_market_profile,
    predict_style_cluster,
    reference_mean,
    top_similar,
)
from .strategy import build_differences, build_market_gaps, build_paths


def run_analysis(audio_path: str, segment_mode: str = "best") -> dict:
    raw = extract_features_from_path(audio_path, segment_mode=segment_mode)
    sound_dna_features = normalize_features(raw)

    style_cluster = predict_style_cluster(sound_dna_features)
    top_refs = top_similar(sound_dna_features, cluster_id=style_cluster["cluster_id"], top_k=3)
    ref_avg = reference_mean(top_refs)
    feature_importance = feature_importance_for_song(sound_dna_features, style_cluster["cluster_id"])
    differences = build_differences(sound_dna_features, ref_avg, feature_importance)
    market_profile = get_market_profile()

    sound_dna = {
        "tempo": round(sound_dna_features["tempo"], 2),
        "energy": round(sound_dna_features["energy"], 3),
        "danceability": round(sound_dna_features["danceability"], 3),
        "valence": round(sound_dna_features["valence"], 3),
        "acousticness": round(sound_dna_features["acousticness"], 3),
        "instrumentalness": round(sound_dna_features["instrumentalness"], 3),
        "speechiness": round(sound_dna_features["speechiness"], 3),
        "loudness": round(sound_dna_features["loudness"], 3),
        "liveness": round(sound_dna_features["liveness"], 3),
        "mfcc_mean_1": round(sound_dna_features["mfcc_mean_1"], 3),
        "mfcc_mean_2": round(sound_dna_features["mfcc_mean_2"], 3),
        "mfcc_mean_3": round(sound_dna_features["mfcc_mean_3"], 3),
        "mfcc_mean_4": round(sound_dna_features["mfcc_mean_4"], 3),
        "mfcc_mean_5": round(sound_dna_features["mfcc_mean_5"], 3),
        "production_style": production_style(sound_dna_features),
        "mood": mood_label(sound_dna_features),
    }

    return {
        "sound_dna": sound_dna,
        "style_cluster": style_cluster,
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
        "market_gaps": build_market_gaps(style_cluster, market_profile),
        "paths": build_paths(),
    }
