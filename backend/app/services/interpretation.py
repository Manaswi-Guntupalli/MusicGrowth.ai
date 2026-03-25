from __future__ import annotations


def production_style(features: dict[str, float]) -> str:
    energy = features["energy"]
    acousticness = features["acousticness"]
    speechiness = features["speechiness"]
    loudness = features["loudness"]

    if energy < 0.45 and acousticness > 0.6:
        return "Lo-fi / intimate"
    if energy > 0.75 and loudness > 0.75:
        return "Polished / high-impact"
    if speechiness > 0.6:
        return "Vocal-forward / speech-heavy"
    if acousticness < 0.35 and energy > 0.6:
        return "Electronic / synthetic"
    return "Balanced indie"


def mood_label(features: dict[str, float]) -> str:
    valence = features["valence"]
    energy = features["energy"]

    if valence < 0.35 and energy < 0.45:
        return "Calm / introspective"
    if valence > 0.65 and energy > 0.6:
        return "Bright / uplifting"
    if energy > 0.7:
        return "Driven / energetic"
    return "Reflective / balanced"


def difference_interpretation(feature: str, delta_percent: float) -> str:
    direction = "higher" if delta_percent > 0 else "lower"
    magnitude = abs(delta_percent)

    if feature == "energy":
        if direction == "lower" and magnitude > 20:
            return "Can read as intimate aesthetic, but may reduce mainstream playlist fit."
        if direction == "higher" and magnitude > 20:
            return "Increases immediate impact and discoverability, but raises competition intensity."
    if feature == "tempo":
        if direction == "lower":
            return "Supports chill or emotional positioning; may slow broad dance uptake."
        return "Improves mainstream momentum and dance context compatibility."
    if feature == "acousticness":
        if direction == "higher":
            return "Signals organic texture and authenticity; less aligned with glossy pop."
        return "Leans into synthetic or polished production character."

    if magnitude < 10:
        return "Near reference norm; unlikely to drive positioning by itself."
    return f"Notably {direction} than reference peers; use intentionally in brand identity."
