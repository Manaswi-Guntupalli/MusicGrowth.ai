from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from typing import Any
from urllib import error, request

from ..core.config import OPENAI_API_KEY, OPENAI_MODEL


_PLACEHOLDER_KEYS = {
    "",
    "sk-demo-placeholder-change-me",
    "replace-with-your-openai-api-key",
    "your-openai-api-key",
}


def _has_openai_key() -> bool:
    return bool(OPENAI_API_KEY) and OPENAI_API_KEY not in _PLACEHOLDER_KEYS


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _feature_note(feature: str, delta: float) -> dict[str, str]:
    if feature == "tempo":
        direction = "up" if delta > 0 else "down"
        explanation = (
            "The tempo moved "
            f"{direction}, which changes perceived pacing and can shift the track toward "
            "either tighter urgency or more relaxed motion."
        )
    elif feature in {"energy", "danceability", "valence", "liveness"}:
        direction = "up" if delta > 0 else "down"
        explanation = (
            f"{feature.capitalize()} moved {direction}, which affects how immediate and expressive the track feels."
        )
    elif feature == "speechiness":
        explanation = "Speechiness changed, which shifts the balance between vocal-forward and music-forward presentation."
    elif feature == "instrumentalness":
        explanation = "Instrumentalness changed, which alters how vocal-free or texture-driven the result sounds."
    else:
        explanation = f"{feature.capitalize()} moved in a way that changes the track's tonal balance and reference fit."

    return {
        "feature": feature,
        "impact": "increase" if delta > 0 else "decrease",
        "explanation": explanation,
    }


def _build_local_explainability(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    changes = list(
        payload.get("adjustments_applied")
        or payload.get("recommended_adjustments")
        or payload.get("simulation", {}).get("adjustments_applied")
        or []
    )
    before = payload.get("before") or payload.get("baseline") or {}
    after = payload.get("after") or payload.get("simulation", {}).get("after") or {}
    insights = list(payload.get("insights") or payload.get("simulation", {}).get("insights") or [])
    objective = payload.get("objective", "similarity")
    optimized_score = payload.get("optimized_score")
    improvement = payload.get("improvement")
    source = "ml-local"

    if kind == "optimization":
        summary = (
            f"The optimizer targeted {objective} and selected a small set of adjustments that improved the score "
            f"by {float(improvement or 0.0):.3f}."
        )
    else:
        summary = (
            "The simulation compares the current profile against a modified version of the same song, "
            "showing how the cluster fit and market score move together."
        )

    why_it_changed: list[str] = []
    if changes:
        ranked = sorted(changes, key=lambda item: abs(float(item.get("delta", 0.0))), reverse=True)
        for row in ranked[:3]:
            feature = str(row.get("feature", "feature"))
            delta = float(row.get("delta", 0.0))
            direction = "increased" if delta > 0 else "decreased"
            why_it_changed.append(
                f"{feature.capitalize()} {direction} by {abs(delta):.3f}, which helped reshape the recommendation." 
            )
    elif insights:
        why_it_changed.append(insights[0])

    tradeoffs: list[str] = []
    similarity_delta = float(payload.get("similarity_delta", 0.0))
    opportunity_delta = float(payload.get("opportunity_delta", 0.0))
    cluster_changed = bool(payload.get("cluster_changed", False))

    if similarity_delta > 0:
        tradeoffs.append("Similarity improved, so the result fits the reference cluster more closely.")
    elif similarity_delta < 0:
        tradeoffs.append("Similarity dropped, so the result is more distinct from the current cluster.")
    else:
        tradeoffs.append("Similarity stayed roughly flat, so the change was more strategic than structural.")

    if opportunity_delta > 0:
        tradeoffs.append("Market opportunity improved, but that may also move the track into a more competitive lane.")
    elif opportunity_delta < 0:
        tradeoffs.append("Market opportunity softened, which can preserve identity but reduce discoverability." )

    if cluster_changed:
        tradeoffs.append("The style cluster shifted, which is a stronger creative repositioning rather than a minor tweak.")

    next_steps: list[str] = []
    if kind == "optimization":
        next_steps.append("Test the suggested deltas on a rough edit before committing to a final mix.")
        next_steps.append("Keep the strongest identity signals while validating the discovery lift.")
    else:
        next_steps.append("Use the simulated changes as an A/B branch, not a final production decision.")
        next_steps.append("Compare the projected cluster move against your brand identity goals.")

    confidence_value = 0.45
    confidence_value += min(0.2, abs(similarity_delta) / 15.0)
    confidence_value += min(0.15, abs(opportunity_delta) / 5.0)
    if changes:
        confidence_value += min(0.15, len(changes) * 0.04)
    if cluster_changed:
        confidence_value -= 0.05
    confidence = round(_clamp01(confidence_value), 3)

    feature_notes = [_feature_note(str(item.get("feature", "feature")), float(item.get("delta", 0.0))) for item in changes[:5]]

    return {
        "source": source,
        "summary": summary,
        "why_it_changed": why_it_changed,
        "tradeoffs": tradeoffs,
        "next_steps": next_steps,
        "feature_notes": feature_notes,
        "confidence": confidence,
        "disclaimer": "This explanation is generated by the local ML engine for the trajectory simulator.",
    }


def _call_openai_for_explanation(kind: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not _has_openai_key():
        return None

    system_message = (
        "You translate structured ML trajectory outputs into user-friendly explanations. "
        "Do not change the model decisions. Do not invent new numbers. "
        "Return ONLY valid JSON."
    )
    user_message = {
        "kind": kind,
        "payload": payload,
        "required_schema": {
            "source": "openai",
            "summary": "string",
            "why_it_changed": ["string"],
            "tradeoffs": ["string"],
            "next_steps": ["string"],
            "feature_notes": [
                {
                    "feature": "string",
                    "impact": "increase|decrease",
                    "explanation": "string",
                }
            ],
            "confidence": "number between 0 and 1",
            "disclaimer": "string",
        },
    }

    body = json.dumps(
        {
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": json.dumps(user_message, ensure_ascii=False)},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")

    req = request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "12"))) as resp:
            response_payload = json.loads(resp.read().decode("utf-8"))
        content = response_payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            return None
        parsed["source"] = "openai"
        if "confidence" in parsed:
            try:
                parsed["confidence"] = round(_clamp01(float(parsed["confidence"])), 3)
            except (TypeError, ValueError):
                parsed["confidence"] = 0.5
        return parsed
    except (error.URLError, error.HTTPError, KeyError, IndexError, ValueError, TimeoutError, json.JSONDecodeError):
        return None


def build_trajectory_explainability(
    kind: str,
    payload: dict[str, Any],
    *,
    allow_openai: bool = True,
) -> dict[str, Any]:
    if allow_openai:
        openai_result = _call_openai_for_explanation(kind, payload)
        if openai_result is not None:
            return openai_result
    return _build_local_explainability(kind, payload)


def _safe_text(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _safe_string_list(value: Any, fallback: list[str], max_items: int = 4) -> list[str]:
    if isinstance(value, list):
        cleaned: list[str] = []
        for row in value:
            text = str(row).strip()
            if text:
                cleaned.append(text)
        if cleaned:
            return cleaned[:max_items]
    return list(fallback[:max_items])


def _default_kpis_for_path(title: str) -> list[str]:
    title_lower = title.lower()
    if "mainstream" in title_lower:
        return [
            "Playlist adds per release week",
            "7-day save rate",
            "Skip rate in first 30 seconds",
            "New listener growth",
        ]

    if "niche" in title_lower:
        return [
            "Returning listener ratio",
            "Completion rate",
            "Fan-library save depth",
            "Community engagement per release",
        ]

    return [
        "Save-to-stream ratio",
        "Completion rate",
        "New listener to returning listener balance",
        "Playlist reach quality score",
    ]


def _build_local_creative_card(path: dict[str, Any]) -> dict[str, Any]:
    title = _safe_text(path.get("title"), "Creative Path")
    strategy = _safe_text(path.get("strategy"), "Strategy details are not available.")
    expected = _safe_text(path.get("expected"), "Expected outcomes are not available.")
    tradeoff = _safe_text(path.get("tradeoff"), "Tradeoffs are not available.")
    actions = _safe_string_list(
        path.get("actions"),
        ["Run a focused A/B production test for this path before final release."],
        max_items=4,
    )

    return {
        "id": _safe_text(path.get("id"), "1"),
        "title": title,
        "summary": f"{title}: {strategy}",
        "rationale": f"Expected impact: {expected} Tradeoff to manage: {tradeoff}",
        "immediate_actions": actions,
        "caution_points": [tradeoff],
        "success_kpis": _default_kpis_for_path(title),
    }


def _build_local_creative_paths_summary(payload: dict[str, Any]) -> dict[str, Any]:
    paths = payload.get("paths")
    if not isinstance(paths, list) or not paths:
        raise ValueError("At least one creative path is required.")

    cards = [_build_local_creative_card(path) for path in paths if isinstance(path, dict)]
    if not cards:
        raise ValueError("At least one valid creative path is required.")

    return {
        "source": "ml-local",
        "generated_at": datetime.now(UTC).isoformat(),
        "cards": cards,
        "disclaimer": "This summary is generated from local model output because an OpenAI response was unavailable.",
    }


def _call_openai_for_creative_paths(payload: dict[str, Any]) -> dict[str, Any] | None:
    if not _has_openai_key():
        return None

    paths = payload.get("paths")
    if not isinstance(paths, list) or not paths:
        return None

    system_message = (
        "You are a senior music growth strategist. "
        "Transform structured ML analysis outcomes into concise, practical, structured guidance "
        "for each creative path. Keep path identities exactly as provided. "
        "Do not invent unsupported numeric metrics. Return ONLY valid JSON."
    )

    user_message = {
        "task": "Summarize all creative paths in a structured format for card-based UI.",
        "payload": payload,
        "required_schema": {
            "cards": [
                {
                    "id": "string, must match path id",
                    "title": "string, must match path title",
                    "summary": "string",
                    "rationale": "string",
                    "immediate_actions": ["string"],
                    "caution_points": ["string"],
                    "success_kpis": ["string"],
                }
            ],
            "disclaimer": "string",
        },
        "rules": [
            "Return one card for each input path.",
            "Keep immediate_actions, caution_points, success_kpis each between 2 and 4 bullets.",
            "Keep language practical and execution-focused.",
        ],
    }

    body = json.dumps(
        {
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": json.dumps(user_message, ensure_ascii=False)},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")

    req = request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "12"))) as resp:
            response_payload = json.loads(resp.read().decode("utf-8"))

        content = response_payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            return None

        raw_cards = parsed.get("cards")
        if not isinstance(raw_cards, list):
            return None

        cards_by_id: dict[str, dict[str, Any]] = {}
        cards_by_title: dict[str, dict[str, Any]] = {}
        for row in raw_cards:
            if not isinstance(row, dict):
                continue
            row_id = str(row.get("id", "")).strip()
            row_title = str(row.get("title", "")).strip().lower()
            if row_id:
                cards_by_id[row_id] = row
            if row_title:
                cards_by_title[row_title] = row

        normalized_cards: list[dict[str, Any]] = []
        for raw_path in paths:
            if not isinstance(raw_path, dict):
                continue

            fallback = _build_local_creative_card(raw_path)
            path_id = _safe_text(raw_path.get("id"), fallback["id"])
            path_title = _safe_text(raw_path.get("title"), fallback["title"])

            candidate = cards_by_id.get(path_id) or cards_by_title.get(path_title.lower()) or {}

            normalized_cards.append(
                {
                    "id": path_id,
                    "title": path_title,
                    "summary": _safe_text(candidate.get("summary"), fallback["summary"]),
                    "rationale": _safe_text(candidate.get("rationale"), fallback["rationale"]),
                    "immediate_actions": _safe_string_list(
                        candidate.get("immediate_actions"),
                        fallback["immediate_actions"],
                        max_items=4,
                    ),
                    "caution_points": _safe_string_list(
                        candidate.get("caution_points"),
                        fallback["caution_points"],
                        max_items=4,
                    ),
                    "success_kpis": _safe_string_list(
                        candidate.get("success_kpis"),
                        fallback["success_kpis"],
                        max_items=4,
                    ),
                }
            )

        if not normalized_cards:
            return None

        disclaimer = _safe_text(
            parsed.get("disclaimer"),
            "Generated with OpenAI based on your analysis outcome and path definitions.",
        )
        return {
            "source": "openai",
            "generated_at": datetime.now(UTC).isoformat(),
            "cards": normalized_cards,
            "disclaimer": disclaimer,
        }
    except (error.URLError, error.HTTPError, KeyError, IndexError, ValueError, TimeoutError, json.JSONDecodeError):
        return None


def build_creative_paths_ai_summary(payload: dict[str, Any]) -> dict[str, Any]:
    openai_result = _call_openai_for_creative_paths(payload)
    if openai_result is not None:
        return openai_result
    return _build_local_creative_paths_summary(payload)