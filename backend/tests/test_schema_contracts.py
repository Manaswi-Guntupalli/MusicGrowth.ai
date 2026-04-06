from __future__ import annotations

from backend.app.models.schemas import AnalysisResponse, DifferenceInsight


def test_difference_insight_includes_tag():
    diff = DifferenceInsight(
        feature="energy",
        song_value=0.72,
        reference_mean=0.65,
        delta_percent=7.0,
        interpretation="Higher than mean",
    )
    payload = diff.model_dump()
    assert "tag" in payload
    assert payload["tag"] == "NORMAL"


def test_analysis_response_contract_parses():
    payload = {
        "sound_dna": {
            "tempo": 120.0,
            "energy": 0.7,
            "danceability": 0.65,
            "valence": 0.45,
            "acousticness": 0.2,
            "instrumentalness": 0.1,
            "speechiness": 0.06,
            "loudness": -8.0,
            "liveness": 0.19,
            "mfcc_mean_1": -20.0,
            "mfcc_mean_2": 8.0,
            "mfcc_mean_3": 2.0,
            "mfcc_mean_4": 6.0,
            "mfcc_mean_5": -3.0,
            "production_style": "Balanced indie",
            "mood": "Reflective / balanced",
        },
        "style_cluster": {
            "cluster_id": 1,
            "label": "Balanced Indie",
            "confidence": 63.2,
            "raw_confidence": 70.1,
        },
        "top_similar": [
            {
                "artist": "Artist",
                "song": "Song",
                "cluster": "Balanced Indie",
                "similarity": 80.0,
            }
        ],
        "differences": [
            {
                "feature": "energy",
                "tag": "OPPORTUNITY",
                "song_value": 0.72,
                "reference_mean": 0.65,
                "delta_percent": 7.0,
                "interpretation": "Higher than mean",
            }
        ],
        "market_gaps": ["Moderate opportunity in current cluster."],
        "paths": [
            {
                "id": "A",
                "title": "Mainstream Acceleration",
                "strategy": "Move closer to high-discoverability profiles.",
                "expected": "Faster pickup.",
                "tradeoff": "Higher competition.",
                "actions": ["Tighten hooks"],
            }
        ],
    }

    parsed = AnalysisResponse(**payload)
    assert parsed.style_cluster.raw_confidence == 70.1
    assert parsed.differences[0].tag == "OPPORTUNITY"
