from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Final

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

from .explainability import build_trajectory_explainability
from .similarity import (
    cluster_membership_probabilities,
    get_market_profile,
    load_reference_dataset,
    predict_style_cluster,
    top_similar,
)
from .sound_dna import FEATURE_ORDER, clamp01

logger = logging.getLogger(__name__)

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


def _env_int(name: str, default: int, minimum: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return max(minimum, default)
    try:
        return max(minimum, int(raw))
    except ValueError:
        return max(minimum, default)


def _env_flag(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw not in {"0", "false", "no", "off"}


MODEL_DIR = Path(__file__).resolve().parent.parent / "data" / "models"
TRAJECTORY_SURROGATE_PATH = MODEL_DIR / "trajectory_surrogate.pkl"
TRAJECTORY_SURROGATE_META_PATH = MODEL_DIR / "trajectory_surrogate_metadata.json"

SURROGATE_CONTROL_ORDER: Final[list[str]] = list(OPTIMIZER_CONTROLS.keys())
SURROGATE_AUTOTRAIN: Final[bool] = _env_flag("TRAJECTORY_SURROGATE_AUTOTRAIN", True)
SURROGATE_BASE_SAMPLES: Final[int] = _env_int("TRAJECTORY_SURROGATE_BASE_SAMPLES", 56, 24)
SURROGATE_VARIANTS_PER_SAMPLE: Final[int] = _env_int("TRAJECTORY_SURROGATE_VARIANTS_PER_SAMPLE", 5, 3)
SURROGATE_CANDIDATE_COUNT: Final[int] = _env_int("TRAJECTORY_SURROGATE_CANDIDATE_COUNT", 180, 60)
SURROGATE_TOPK_EVAL: Final[int] = _env_int("TRAJECTORY_SURROGATE_TOPK_EVAL", 24, 8)


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


def _apply_adjustments(base_features: dict[str, float], adjustments: dict[str, float]) -> tuple[dict[str, float], list[dict]]:
    candidate = dict(base_features)
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

    return candidate, changes


def _evaluate_against_baseline(
    baseline_snapshot: dict,
    candidate_features: dict[str, float],
) -> tuple[dict, float, float, bool]:
    after = _snapshot(candidate_features)
    similarity_delta = round(float(after["avg_similarity"] - baseline_snapshot["avg_similarity"]), 2)
    opportunity_delta = round(float(after["opportunity_score"] - baseline_snapshot["opportunity_score"]), 6)
    cluster_changed = int(after["style_cluster"]["cluster_id"]) != int(baseline_snapshot["style_cluster"]["cluster_id"])
    return after, similarity_delta, opportunity_delta, cluster_changed


def _build_insights(
    changes: list[dict],
    before: dict,
    after: dict,
    similarity_delta: float,
    opportunity_delta: float,
    cluster_changed: bool,
) -> list[str]:
    _ = after

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

    return insights


def _changes_to_delta_map(changes: list[dict], allowed: set[str] | None = None) -> dict[str, float]:
    delta_map: dict[str, float] = {}
    for row in changes:
        feature = str(row.get("feature", "")).strip()
        if not feature:
            continue
        if allowed is not None and feature not in allowed:
            continue
        try:
            delta = float(row.get("delta", 0.0))
        except (TypeError, ValueError):
            continue
        if abs(delta) >= 1e-9:
            delta_map[feature] = delta
    return delta_map


def _surrogate_input_vector(base_features: dict[str, float], deltas: dict[str, float]) -> list[float]:
    row = [float(base_features[name]) for name in FEATURE_ORDER]
    row.extend(float(deltas.get(name, 0.0)) for name in SURROGATE_CONTROL_ORDER)
    return row


def _extract_reference_features(row: dict) -> dict[str, float] | None:
    raw_features = row.get("features")
    if not isinstance(raw_features, dict):
        return None

    out: dict[str, float] = {}
    for name in FEATURE_ORDER:
        try:
            out[name] = float(raw_features[name])
        except (KeyError, TypeError, ValueError):
            return None
    return out


def _sample_base_profiles(rng: np.random.RandomState, sample_count: int) -> list[dict[str, float]]:
    refs = load_reference_dataset()
    if not refs:
        return []

    target = min(sample_count, len(refs))
    selected: list[dict[str, float]] = []

    seen_indices: set[int] = set()
    attempt_budget = max(target * 25, target + 50)
    while len(selected) < target and len(seen_indices) < len(refs) and attempt_budget > 0:
        attempt_budget -= 1
        idx = int(rng.randint(0, len(refs)))
        if idx in seen_indices:
            continue
        seen_indices.add(idx)

        features = _extract_reference_features(refs[idx])
        if features is not None:
            selected.append(features)

    if len(selected) >= target:
        return selected

    for row in refs:
        features = _extract_reference_features(row)
        if features is None:
            continue
        selected.append(features)
        if len(selected) >= target:
            break

    return selected


def _random_adjustment_candidate(
    rng: np.random.RandomState,
    allowed_features: list[str],
) -> dict[str, float]:
    candidate: dict[str, float] = {}
    for feature in allowed_features:
        step, limit = OPTIMIZER_CONTROLS[feature]
        draw = float(rng.rand())
        if draw < 0.55:
            continue

        magnitude = float(rng.uniform(step, limit))
        candidate[feature] = magnitude if rng.rand() >= 0.5 else -magnitude

    if not candidate and allowed_features:
        idx = int(rng.randint(0, len(allowed_features)))
        feature = allowed_features[idx]
        step, _ = OPTIMIZER_CONTROLS[feature]
        candidate[feature] = step if rng.rand() >= 0.5 else -step

    return candidate


def _ensure_model_dir() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)


def _load_trajectory_surrogate_from_disk() -> dict | None:
    if not TRAJECTORY_SURROGATE_PATH.exists():
        return None
    try:
        bundle = joblib.load(TRAJECTORY_SURROGATE_PATH)
    except Exception as exc:  # pragma: no cover - defensive cache read
        logger.warning("Failed to load trajectory surrogate model: %s", exc)
        return None

    if not isinstance(bundle, dict):
        return None
    if "similarity_model" not in bundle or "opportunity_model" not in bundle:
        return None
    return bundle


def _train_trajectory_surrogate() -> dict | None:
    rng = np.random.RandomState(42)
    base_profiles = _sample_base_profiles(rng, SURROGATE_BASE_SAMPLES)
    if len(base_profiles) < 12:
        return None

    X_rows: list[list[float]] = []
    y_similarity: list[float] = []
    y_opportunity: list[float] = []

    for base in base_profiles:
        try:
            baseline_snapshot = _snapshot(base)
        except Exception:
            continue

        for _ in range(SURROGATE_VARIANTS_PER_SAMPLE):
            proposed = _random_adjustment_candidate(rng, SURROGATE_CONTROL_ORDER)
            candidate_features, changes = _apply_adjustments(base, proposed)
            if not changes:
                continue

            applied_deltas = _changes_to_delta_map(changes)
            if not applied_deltas:
                continue

            try:
                _, similarity_delta, opportunity_delta, _ = _evaluate_against_baseline(
                    baseline_snapshot,
                    candidate_features,
                )
            except Exception:
                continue

            X_rows.append(_surrogate_input_vector(base, applied_deltas))
            y_similarity.append(float(similarity_delta))
            y_opportunity.append(float(opportunity_delta))

    if len(X_rows) < 96:
        logger.warning(
            "Trajectory surrogate training skipped due to insufficient rows: %s",
            len(X_rows),
        )
        return None

    X = np.asarray(X_rows, dtype=np.float32)
    y_sim = np.asarray(y_similarity, dtype=np.float32)
    y_opp = np.asarray(y_opportunity, dtype=np.float32)

    similarity_model = HistGradientBoostingRegressor(
        learning_rate=0.05,
        max_depth=7,
        max_iter=260,
        min_samples_leaf=12,
        random_state=42,
    )
    opportunity_model = HistGradientBoostingRegressor(
        learning_rate=0.05,
        max_depth=7,
        max_iter=260,
        min_samples_leaf=12,
        random_state=43,
    )

    similarity_model.fit(X, y_sim)
    opportunity_model.fit(X, y_opp)

    sim_pred = similarity_model.predict(X)
    opp_pred = opportunity_model.predict(X)
    sim_mae = float(np.mean(np.abs(sim_pred - y_sim)))
    opp_mae = float(np.mean(np.abs(opp_pred - y_opp)))

    bundle = {
        "similarity_model": similarity_model,
        "opportunity_model": opportunity_model,
        "feature_order": list(FEATURE_ORDER),
        "control_order": list(SURROGATE_CONTROL_ORDER),
    }

    _ensure_model_dir()
    joblib.dump(bundle, TRAJECTORY_SURROGATE_PATH)

    meta = {
        "model": "hist_gradient_boosting_surrogate",
        "rows": int(len(X_rows)),
        "feature_count": int(X.shape[1]),
        "base_samples": int(len(base_profiles)),
        "variants_per_sample": int(SURROGATE_VARIANTS_PER_SAMPLE),
        "similarity_train_mae": round(sim_mae, 6),
        "opportunity_train_mae": round(opp_mae, 6),
    }
    TRAJECTORY_SURROGATE_META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    logger.info(
        "Trajectory surrogate trained with %s rows (sim_mae=%0.4f, opp_mae=%0.4f)",
        len(X_rows),
        sim_mae,
        opp_mae,
    )
    return bundle


@lru_cache(maxsize=1)
def _get_trajectory_surrogate() -> dict | None:
    from_disk = _load_trajectory_surrogate_from_disk()
    if from_disk is not None:
        return from_disk

    if not SURROGATE_AUTOTRAIN:
        return None

    try:
        return _train_trajectory_surrogate()
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("Trajectory surrogate auto-train failed: %s", exc)
        return None


def train_trajectory_surrogate_model(force_retrain: bool = False) -> dict[str, object]:
    if force_retrain:
        try:
            TRAJECTORY_SURROGATE_PATH.unlink(missing_ok=True)
            TRAJECTORY_SURROGATE_META_PATH.unlink(missing_ok=True)
        except OSError:
            pass

    trained = _train_trajectory_surrogate()
    _get_trajectory_surrogate.cache_clear()
    _ = _get_trajectory_surrogate()

    if trained is None:
        raise RuntimeError("Unable to train trajectory surrogate model.")

    if TRAJECTORY_SURROGATE_META_PATH.exists():
        try:
            return json.loads(TRAJECTORY_SURROGATE_META_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    return {
        "model": "hist_gradient_boosting_surrogate",
        "path": str(TRAJECTORY_SURROGATE_PATH),
    }


def _predict_surrogate_gain(
    surrogate: dict,
    base_features: dict[str, float],
    deltas: dict[str, float],
    objective: str,
) -> float:
    vector = np.asarray([_surrogate_input_vector(base_features, deltas)], dtype=np.float32)
    sim_gain = float(surrogate["similarity_model"].predict(vector)[0])
    opp_gain = float(surrogate["opportunity_model"].predict(vector)[0])
    if objective == "opportunity":
        return opp_gain
    return sim_gain


def _seed_adjustments_with_surrogate(
    baseline: dict[str, float],
    baseline_snapshot: dict,
    objective: str,
    allowed: list[str],
) -> dict[str, float]:
    surrogate = _get_trajectory_surrogate()
    if surrogate is None:
        return {}

    allowed_set = set(allowed)

    seed_value = 17
    for idx, feature in enumerate(FEATURE_ORDER):
        seed_value += int(abs(float(baseline[feature])) * float(idx + 11))
    rng = np.random.RandomState(seed_value % (2**31 - 1))

    ranked_candidates: list[tuple[float, dict[str, float]]] = []
    seen_keys: set[tuple[float, ...]] = set()

    for _ in range(SURROGATE_CANDIDATE_COUNT):
        proposed = _random_adjustment_candidate(rng, allowed)
        _, changes = _apply_adjustments(baseline, proposed)
        deltas = _changes_to_delta_map(changes, allowed_set)
        if not deltas:
            continue

        key = tuple(round(float(deltas.get(name, 0.0)), 4) for name in allowed)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        predicted_gain = _predict_surrogate_gain(surrogate, baseline, deltas, objective)
        ranked_candidates.append((predicted_gain, deltas))

    if not ranked_candidates:
        return {}

    ranked_candidates.sort(key=lambda row: row[0], reverse=True)

    best_gain = 0.0
    best_deltas: dict[str, float] = {}

    for _, deltas in ranked_candidates[:SURROGATE_TOPK_EVAL]:
        candidate_features, candidate_changes = _apply_adjustments(baseline, deltas)
        if not candidate_changes:
            continue

        _, sim_delta, opp_delta, _ = _evaluate_against_baseline(baseline_snapshot, candidate_features)
        realized_gain = opp_delta if objective == "opportunity" else sim_delta
        if realized_gain > (best_gain + 1e-9):
            best_gain = realized_gain
            best_deltas = _changes_to_delta_map(candidate_changes, allowed_set)

    return best_deltas


def run_trajectory_simulation(base_features: dict[str, float], adjustments: dict[str, float]) -> dict:
    missing = [name for name in FEATURE_ORDER if name not in base_features]
    if missing:
        raise ValueError(f"Missing base feature(s): {', '.join(missing)}")

    baseline = {name: float(base_features[name]) for name in FEATURE_ORDER}
    candidate, changes = _apply_adjustments(baseline, adjustments)

    before = _snapshot(baseline)
    after, similarity_delta, opportunity_delta, cluster_changed = _evaluate_against_baseline(before, candidate)
    insights = _build_insights(changes, before, after, similarity_delta, opportunity_delta, cluster_changed)

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
        allow_openai=False,
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

    seeded_deltas = _seed_adjustments_with_surrogate(
        baseline=baseline,
        baseline_snapshot=baseline_snapshot,
        objective=objective,
        allowed=allowed,
    )
    if seeded_deltas:
        seeded_features, seeded_changes = _apply_adjustments(current, seeded_deltas)
        if seeded_changes:
            current = seeded_features
            seeded_map = _changes_to_delta_map(seeded_changes, set(allowed))
            for feature, delta in seeded_map.items():
                _, limit = OPTIMIZER_CONTROLS[feature]
                deltas[feature] = max(-limit, min(limit, delta))

            best_snapshot = _snapshot(current)
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
        allow_openai=False,
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
