"""Heuristic baseline scorer and optional Groq LLM evaluator.

The heuristic is a reproducible baseline, not a substitute for editor review.
Set GROQ_API_KEY and optionally GROQ_MODEL to enable LLM-assisted evaluation.
"""
from __future__ import annotations

import json
import os


WEIGHTS = {
    "hook": 0.25,
    "cliffhanger": 0.25,
    "emotion": 0.20,
    "standalone": 0.20,
    "coherence": 0.10,
}

HOOK_TERMS = [
    "what", "why", "no", "never", "stop", "don't", "you should",
    "look", "wait", "because", "marrying", "betray", "secret",
]
CLIFF_TERMS = [
    "will you", "accept", "who are you", "what happened", "please",
    "i swear", "you don't know", "the truth", "marry", "choose",
]
EMOTION_TERMS = [
    "cry", "tears", "heartbroken", "shocked", "furious", "love",
    "hate", "betray", "desperate", "screaming", "begging",
]


def _hits(text: str, terms: list[str]) -> int:
    text_lower = text.lower()
    return sum(1 for term in terms if term in text_lower)


def _event_text(events: list, predicate=None) -> str:
    parts = []
    for event in events:
        if not isinstance(event, dict):
            continue
        if predicate is not None and not predicate(event):
            continue
        text = event.get("text")
        if text:
            parts.append(str(text))
    return " ".join(parts)


def _number(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def heuristic_evaluate(candidate: dict) -> dict:
    """Score a candidate using deterministic keyword and structure signals."""
    events = candidate.get("events") or []
    if not isinstance(events, list):
        events = []

    segments = candidate.get("segments") or []
    first_segment = segments[0] if segments and isinstance(segments[0], dict) else {}
    segment_start = _number(first_segment.get("start_seconds"))
    segment_end = _number(first_segment.get("end_seconds"))
    duration = _number(candidate.get("duration_seconds"))

    first_three = [
        event for event in events
        if isinstance(event, dict)
        and _number(event.get("start"), float("inf")) < segment_start + 3
        and _number(event.get("end"), float("-inf")) > segment_start
    ]
    last_five_start = segment_end - 5
    last_five = [
        event for event in events
        if isinstance(event, dict)
        and _number(event.get("end"), float("-inf")) > last_five_start
        and _number(event.get("start"), float("inf")) < segment_end
    ]

    hook_text = _event_text(first_three)
    ending_text = _event_text(last_five)
    transcript = str(candidate.get("transcript") or _event_text(events))

    hook_score = min(10, 3 + 1.5 * _hits(hook_text, HOOK_TERMS)
                     + (2 if first_three else 0))
    cliffhanger_score = min(
        10,
        2 + 1.6 * _hits(ending_text, CLIFF_TERMS)
        + (2 if "?" in ending_text else 0),
    )
    emotion_score = min(10, 2 + 1.4 * _hits(transcript, EMOTION_TERMS))
    dialogue_count = sum(
        1 for event in events
        if isinstance(event, dict) and event.get("kind") == "dialogue"
    )
    standalone_score = min(
        10,
        4 + (2 if candidate.get("logline") else 0)
        + (2 if dialogue_count >= 3 else 0),
    )
    coherence_score = min(
        10,
        4 + (2 if events else 0) + (2 if duration >= 25 else 0),
    )

    scores = {
        "hook": round(hook_score, 1),
        "cliffhanger": round(cliffhanger_score, 1),
        "emotion": round(emotion_score, 1),
        "standalone": round(standalone_score, 1),
        "coherence": round(coherence_score, 1),
    }
    total_score = round(
        sum(scores[key] * WEIGHTS[key] for key in WEIGHTS),
        2,
    )

    return {
        "scores": scores,
        "total_score": total_score,
        "evaluation_method": "heuristic",
        "hook": hook_text[:300] or "No dialogue/action detected in first 3 seconds.",
        "cliffhanger": ending_text[:300] or "No clear ending event detected.",
        "why_it_works": (
            "Baseline keyword and structure score; editor review required."
        ),
        "risk_flags": [
            "Heuristic scores may overrate keyword matches."
        ],
    }


def _normalize_llm_result(result: dict, model: str) -> dict:
    if not isinstance(result, dict):
        raise ValueError("LLM response must be a JSON object.")

    raw_scores = result.get("scores")
    if not isinstance(raw_scores, dict):
        raise ValueError("LLM response is missing a scores object.")

    scores = {}
    for key in WEIGHTS:
        try:
            score = float(raw_scores.get(key, 0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"LLM returned an invalid {key} score.") from exc
        if not 0 <= score <= 10:
            raise ValueError(f"LLM {key} score must be between 0 and 10.")
        scores[key] = score

    risk_flags = result.get("risk_flags", [])
    if not isinstance(risk_flags, list):
        risk_flags = [str(risk_flags)]

    normalized = dict(result)
    normalized.update({
        "scores": scores,
        "total_score": round(
            sum(scores[key] * WEIGHTS[key] for key in WEIGHTS),
            2,
        ),
        "evaluation_method": f"llm:{model}",
        "hook": str(result.get("hook", "")),
        "cliffhanger": str(result.get("cliffhanger", "")),
        "why_it_works": str(result.get("why_it_works", "")),
        "risk_flags": [str(flag) for flag in risk_flags],
    })
    return normalized


def llm_evaluate(candidate: dict, model: str | None = None) -> dict:
    """Evaluate a candidate with Groq, when credentials and package exist."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    try:
        from groq import Groq
    except ImportError as exc:
        raise RuntimeError("Install the optional groq package.") from exc

    model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    prompt = f"""Evaluate this screenplay excerpt as a standalone social-media promo.
Only use evidence in the excerpt. Do not invent events or dialogue.
A valid promo is 20–60 seconds, starts with a compelling hook in its first 3 seconds,
ends at an unresolved cliffhanger, and makes sense to a first-time viewer.
Return ONLY valid JSON with keys: scores (hook, cliffhanger, emotion, standalone,
coherence; each number from 0 to 10), hook (brief evidence/description),
cliffhanger (brief evidence/description), why_it_works (one sentence),
risk_flags (array of strings). Be conservative and flag missing context.
Episode: {candidate.get('episode', 'unknown')}
Logline: {candidate.get('logline', '')}
Clip: {candidate.get('segments', [])}
Transcript:
{str(candidate.get('transcript', ''))[:12000]}
"""

    response = Groq(api_key=api_key).chat.completions.create(
        model=model,
        temperature=0.1,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("LLM returned an empty response.")

    return _normalize_llm_result(json.loads(content), model)


def evaluate(candidate: dict, use_llm: bool = False) -> dict:
    """Evaluate a candidate, using the heuristic as a safe fallback."""
    if not isinstance(candidate, dict):
        raise TypeError("Candidate must be a dictionary.")

    if use_llm:
        try:
            return llm_evaluate(candidate)
        except Exception as exc:
            result = heuristic_evaluate(candidate)
            result["risk_flags"].append(
                f"LLM unavailable; heuristic fallback used: {exc}"
            )
            result["evaluation_method"] = "heuristic_fallback"
            return result

    return heuristic_evaluate(candidate)
