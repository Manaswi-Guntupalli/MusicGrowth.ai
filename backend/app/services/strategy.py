from __future__ import annotations

from .interpretation import difference_interpretation


def build_differences(song: dict[str, float], ref_mean: dict[str, float]) -> list[dict]:
    important = ["energy", "tempo", "acousticness", "danceability", "valence"]
    diffs: list[dict] = []

    for name in important:
        ref = ref_mean[name] if ref_mean[name] != 0 else 0.0001
        delta_pct = ((song[name] - ref) / ref) * 100
        diffs.append(
            {
                "feature": name,
                "song_value": round(song[name], 3),
                "reference_mean": round(ref_mean[name], 3),
                "delta_percent": round(delta_pct, 1),
                "interpretation": difference_interpretation(name, delta_pct),
            }
        )

    diffs.sort(key=lambda x: abs(x["delta_percent"]), reverse=True)
    return diffs


def build_market_gaps(song: dict[str, float]) -> list[str]:
    gaps: list[str] = []
    if song["energy"] < 0.45 and song["valence"] > 0.55:
        gaps.append("Low-energy but positive-emotion zone appears underrepresented in pop references.")
    if song["acousticness"] > 0.65 and song["danceability"] > 0.55:
        gaps.append("Acoustic-dance crossover can open a niche between indie and rhythmic playlists.")
    if song["instrumentalness"] > 0.55 and song["speechiness"] < 0.2:
        gaps.append("High-instrumental, low-vocal profile fits focus and ambient growth segments.")
    if not gaps:
        gaps.append("No strong blue-ocean signal detected; differentiation likely comes from storytelling and branding.")
    return gaps


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
