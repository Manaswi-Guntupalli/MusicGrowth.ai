from __future__ import annotations

from .interpretation import difference_interpretation
from .sound_dna import CORE_FEATURES

DIFF_TAG_KEY = "KEY_DIFFERENTIATOR"
DIFF_TAG_OPPORTUNITY = "OPPORTUNITY"
DIFF_TAG_NORMAL = "NORMAL"


def build_differences(
    song: dict[str, float],
    ref_mean: dict[str, float],
    feature_importance: dict[str, float],
    delta_threshold: float = 0.2,
) -> list[dict]:
    diffs: list[dict] = []

    for name in CORE_FEATURES:
        ref = float(ref_mean.get(name, 0.0))
        song_val = float(song.get(name, 0.0))

        if name == "tempo":
            delta_ratio = (song_val - ref) / max(abs(ref), 1.0)
        elif name == "loudness":
            delta_ratio = (song_val - ref) / max(abs(ref), 1.0)
        else:
            delta_ratio = song_val - ref

        delta_pct = delta_ratio * 100.0
        importance = float(feature_importance.get(name, 0.0))
        is_key = abs(delta_ratio) > delta_threshold and importance >= 0.08
        is_opportunity = abs(delta_ratio) > delta_threshold and not is_key

        if is_key:
            tag = DIFF_TAG_KEY
        elif is_opportunity:
            tag = DIFF_TAG_OPPORTUNITY
        else:
            tag = DIFF_TAG_NORMAL

        diffs.append(
            {
                "feature": name,
                "tag": tag,
                "song_value": round(song_val, 3),
                "reference_mean": round(ref, 3),
                "delta_percent": round(delta_pct, 1),
                "interpretation": difference_interpretation(name, delta_pct),
            }
        )

    diffs.sort(key=lambda x: abs(x["delta_percent"]), reverse=True)
    return diffs


def build_market_gaps(style_cluster: dict, market_profile: dict[str, dict[str, float]]) -> list[str]:
    def percentile(values: list[float], q: float) -> float:
        if not values:
            return 0.0

        ordered = sorted(values)
        if len(ordered) == 1:
            return ordered[0]

        q_clamped = max(0.0, min(1.0, q))
        index = (len(ordered) - 1) * q_clamped
        lower = int(index)
        upper = min(lower + 1, len(ordered) - 1)
        if lower == upper:
            return ordered[lower]

        blend = index - lower
        return ordered[lower] + (ordered[upper] - ordered[lower]) * blend

    cluster_id = style_cluster.get("cluster_id")
    cluster_key = str(cluster_id)
    profile = market_profile.get(cluster_key)

    if profile is None:
        return ["Moderate opportunity detected in adjacent clusters; refine release strategy with small A/B tests."]

    demand = float(profile.get("demand", 0.0))
    saturation = float(profile.get("saturation", 1.0))
    opportunity_score = float(profile.get("opportunity_score", demand / max(1.0, saturation)))

    score_values = [float(row.get("opportunity_score", 0.0)) for row in market_profile.values()]
    if score_values:
        high_threshold = percentile(score_values, 0.75)
        moderate_threshold = percentile(score_values, 0.35)
    else:
        # Defaults align with demand/saturation scores around 0.0x for dense clusters.
        high_threshold = 0.03
        moderate_threshold = 0.015

    if opportunity_score >= high_threshold:
        zone = "High"
    elif opportunity_score >= moderate_threshold:
        zone = "Moderate"
    else:
        zone = "Emerging"

    return [
        (
            f"{zone} opportunity in {style_cluster.get('label', 'current')} cluster "
            f"(demand={demand:.1f}, saturation={saturation:.0f}, score={opportunity_score:.5f})."
        )
    ]


def build_paths() -> list[dict]:
    return [
        {
            "id": "A",
            "title": "Mainstream Acceleration",
            "strategy": "Move closer to high-discoverability profiles.",
            "expected": "Historically faster playlist pickup and broader first-time reach.",
            "tradeoff": "Higher competition and potential identity dilution.",
            "actions": [
                "Increase perceived energy by 15-25% through arrangement and mix punch.",
                "Tighten hook sections for quicker retention.",
                "Reduce long ambient intros in release versions.",
            ],
        },
        {
            "id": "B",
            "title": "Niche Depth",
            "strategy": "Lean into current differentiators and artistic signature.",
            "expected": "Slower top-line growth but stronger fan loyalty and replay quality.",
            "tradeoff": "Smaller immediate audience and longer discovery runway.",
            "actions": [
                "Amplify unique texture choices and signature transitions.",
                "Build a cohesive 3-5 track sonic arc.",
                "Target niche playlists and community channels.",
            ],
        },
        {
            "id": "C",
            "title": "Hybrid Positioning",
            "strategy": "Keep identity core while adding selected mainstream traits.",
            "expected": "Balanced growth curve with moderate reach and solid fan quality.",
            "tradeoff": "Requires disciplined testing and iterative releases.",
            "actions": [
                "Keep about 60% core identity and 40% discoverability optimizations.",
                "A/B test edits with short-form audiences before full release.",
                "Track save-rate vs skip-rate to decide next release direction.",
            ],
        },
    ]
