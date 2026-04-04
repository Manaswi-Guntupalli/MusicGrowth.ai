from __future__ import annotations

from typing import Final

from .explainability import build_trajectory_explainability
from .similarity import cluster_membership_probabilities, get_market_profile, predict_style_cluster, top_similar
from .sound_dna import FEATURE_ORDER, clamp01

UNIT_INTERVAL_FEATURES: Final[set[str]] = {
    "energy",
    "danceability",
    "valence",
    "acousticness",
    "instrumentalness",
    "liveness",
    "speechiness",
}

FEATURE_BOUNDS: Final[dict[str, tuple[float, float]]] = {
    "tempo": (60.0, 220.0),
    "loudness": (-35.0, -3.0),
    "mfcc_mean_1": (-250.0, 50.0),
    "mfcc_mean_2": (-250.0, 250.0),
    "mfcc_mean_3": (-250.0, 250.0),
    "mfcc_mean_4": (-250.0, 250.0),
    "mfcc_mean_5": (-250.0, 250.0),
}

OPTIMIZER_CONTROLS: Final[dict[str, tuple[float, float]]] = {
    "tempo": (2.0, 20.0),
    "energy": (0.02, 0.2),
    "danceability": (0.02, 0.2),
    "valence": (0.02, 0.2),
    "acousticness": (0.02, 0.2),
    "instrumentalness": (0.02, 0.2),
    "liveness": (0.02, 0.2),
    "speechiness": (0.02, 0.2),
    "loudness": (0.5, 6.0),
}


def _bounded(feature: str, value: float) -> float:
    if feature in UNIT_INTERVAL_FEATURES:
        return clamp01(value)
    if feature in FEATURE_BOUNDS:
        lo, hi = FEATURE_BOUNDS[feature]
        return max(lo, min(hi, value))
    return value


def _mean_similarity(rows: list[dict]) -> float:
    if not rows:
        return 0.0
    return sum(float(item.get("similarity", 0.0)) for item in rows) / float(len(rows))


def _expected_market_stats(features: dict[str, float]) -> dict[str, float]:
    profile = get_market_profile()
    memberships = cluster_membership_probabilities(features)

    demand = 0.0
    saturation = 0.0
    opportunity = 0.0

    for cluster_id, weight in memberships.items():
        row = profile.get(str(cluster_id), {})
        demand += float(weight) * float(row.get("demand", 0.0))
        saturation += float(weight) * float(row.get("saturation", 0.0))
        opportunity += float(weight) * float(row.get("opportunity_score", 0.0))

    return {
        "demand": demand,
        "saturation": saturation,
        "opportunity_score": opportunity,
    }


def _snapshot(features: dict[str, float]) -> dict:
    cluster = predict_style_cluster(features)
    top_refs = top_similar(features, cluster_id=cluster["cluster_id"], top_k=3)
    market = _expected_market_stats(features)

    return {
        "style_cluster": cluster,
        "avg_similarity": round(_mean_similarity(top_refs), 2),
        "market_demand": round(market["demand"], 3),
        "market_saturation": round(market["saturation"], 3),
        "opportunity_score": round(market["opportunity_score"], 6),
        "top_similar": [
            {
                "artist": row["artist"],
                "song": row["song"],
                "cluster": row["cluster"],
                "similarity": row["similarity"],
            }
            for row in top_refs
        ],
    }


def _objective_value(snapshot: dict, objective: str) -> float:
    if objective == "opportunity":
        return float(snapshot["opportunity_score"])
    return float(snapshot["avg_similarity"])


def run_trajectory_simulation(base_features: dict[str, float], adjustments: dict[str, float]) -> dict:
    missing = [name for name in FEATURE_ORDER if name not in base_features]
    if missing:
        raise ValueError(f"Missing base feature(s): {', '.join(missing)}")

    baseline = {name: float(base_features[name]) for name in FEATURE_ORDER}
    candidate = dict(baseline)

    changes: list[dict] = []
    for feature, raw_delta in adjustments.items():
        if feature not in FEATURE_ORDER:
            continue

        delta = float(raw_delta)
        if abs(delta) < 1e-9:
            continue

        before = float(candidate[feature])
        after = _bounded(feature, before + delta)
        applied_delta = after - before
        candidate[feature] = after

        if abs(applied_delta) >= 1e-9:
            changes.append(
                {
                    "feature": feature,
                    "before": round(before, 4),
                    "after": round(after, 4),
                    "delta": round(applied_delta, 4),
                }
            )

    before = _snapshot(baseline)
    after = _snapshot(candidate)

    similarity_delta = round(float(after["avg_similarity"] - before["avg_similarity"]), 2)
    opportunity_delta = round(float(after["opportunity_score"] - before["opportunity_score"]), 6)
    cluster_changed = int(after["style_cluster"]["cluster_id"]) != int(before["style_cluster"]["cluster_id"])

    insights: list[str] = []
    if not changes:
        insights.append("No effective feature adjustments were applied.")
    if cluster_changed:
        insights.append(
            f"Cluster shift: {before['style_cluster']['label']} -> {after['style_cluster']['label']}."
        )
    else:
        insights.append("Cluster identity stayed stable under this A/B scenario.")

    if similarity_delta > 1.0:
        insights.append(f"Reference similarity improved by {similarity_delta:.2f} points.")
    elif similarity_delta < -1.0:
        insights.append(f"Reference similarity dropped by {abs(similarity_delta):.2f} points.")
    else:
        insights.append("Reference similarity is mostly unchanged.")

    if opportunity_delta > 0.05:
        insights.append(f"Market opportunity score improved by {opportunity_delta:.3f}.")
    elif opportunity_delta < -0.05:
        insights.append(f"Market opportunity score decreased by {abs(opportunity_delta):.3f}.")
    else:
        insights.append("Market opportunity remains near baseline.")

    explainability = build_trajectory_explainability(
        "simulation",
        {
            "before": before,
            "after": after,
            "cluster_changed": cluster_changed,
            "similarity_delta": similarity_delta,
            "opportunity_delta": opportunity_delta,
            "adjustments_applied": changes,
            "insights": insights,
        },
    )

    return {
        "before": before,
        "after": after,
        "cluster_changed": cluster_changed,
        "similarity_delta": similarity_delta,
        "opportunity_delta": opportunity_delta,
        "adjustments_applied": changes,
        "insights": insights,
        "explainability": explainability,
    }


def run_auto_optimize(
    base_features: dict[str, float],
    objective: str = "similarity",
    adjustable_features: list[str] | None = None,
) -> dict:
    objective = (objective or "similarity").strip().lower()
    if objective not in {"similarity", "opportunity"}:
        raise ValueError("objective must be 'similarity' or 'opportunity'.")

    missing = [name for name in FEATURE_ORDER if name not in base_features]
    if missing:
        raise ValueError(f"Missing base feature(s): {', '.join(missing)}")

    if adjustable_features:
        allowed = [f for f in adjustable_features if f in OPTIMIZER_CONTROLS]
        if not allowed:
            raise ValueError("No valid adjustable_features were provided.")
    else:
        allowed = list(OPTIMIZER_CONTROLS.keys())

    baseline = {name: float(base_features[name]) for name in FEATURE_ORDER}
    current = dict(baseline)
    deltas: dict[str, float] = {name: 0.0 for name in allowed}

    baseline_snapshot = _snapshot(baseline)
    best_snapshot = baseline_snapshot
    best_score = _objective_value(best_snapshot, objective)

    max_passes = 4
    epsilon = 1e-6

    for _ in range(max_passes):
        changed_this_pass = False

        for feature in allowed:
            step, limit = OPTIMIZER_CONTROLS[feature]

            local_best_score = best_score
            local_best_snapshot = best_snapshot
            local_best_direction = 0.0

            for direction in (1.0, -1.0):
                proposed_total = deltas[feature] + (direction * step)
                if abs(proposed_total) > (limit + epsilon):
                    continue

                candidate_features = dict(current)
                before_val = float(candidate_features[feature])
                after_val = _bounded(feature, before_val + direction * step)
                applied = after_val - before_val
                if abs(applied) < epsilon:
                    continue

                candidate_features[feature] = after_val
                candidate_snapshot = _snapshot(candidate_features)
                candidate_score = _objective_value(candidate_snapshot, objective)

                if candidate_score > (local_best_score + epsilon):
                    local_best_score = candidate_score
                    local_best_snapshot = candidate_snapshot
                    local_best_direction = applied

            if abs(local_best_direction) >= epsilon:
                deltas[feature] = round(deltas[feature] + local_best_direction, 6)
                current[feature] = _bounded(feature, current[feature] + local_best_direction)
                best_score = local_best_score
                best_snapshot = local_best_snapshot
                changed_this_pass = True

        if not changed_this_pass:
            break

    recommended_adjustments: dict[str, float] = {}
    for feature, delta in deltas.items():
        if abs(delta) >= epsilon:
            recommended_adjustments[feature] = delta

    simulation = run_trajectory_simulation(baseline, recommended_adjustments)
    optimized_score = _objective_value(best_snapshot, objective)
    explainability = build_trajectory_explainability(
        "optimization",
        {
            "objective": objective,
            "baseline": baseline_snapshot,
            "simulation": simulation,
            "optimized_score": optimized_score,
            "improvement": optimized_score - _objective_value(baseline_snapshot, objective),
            "recommended_adjustments": simulation["adjustments_applied"],
        },
    )

    return {
        "objective": objective,
        "baseline_score": round(_objective_value(baseline_snapshot, objective), 6),
        "optimized_score": round(optimized_score, 6),
        "improvement": round(optimized_score - _objective_value(baseline_snapshot, objective), 6),
        "recommended_adjustments": simulation["adjustments_applied"],
        "simulation": simulation,
        "explainability": explainability,
    }
