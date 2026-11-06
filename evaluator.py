"""Promo quality checks and human-review summary generation."""
from __future__ import annotations

import math


def _valid_duration(value) -> bool:
    try:
        duration = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(duration) and 20 <= duration <= 60


def validate_promo(promo: dict) -> list[str]:
    """Return validation and review messages for a promo result."""
    if not isinstance(promo, dict):
        return ["Promo must be a dictionary."]

    issues = []
    duration = promo.get("duration_seconds")

    if not _valid_duration(duration):
        issues.append("Duration is outside the required 20–60 second range.")

    segments = promo.get("segments")
    if not isinstance(segments, list) or not segments:
        issues.append("No segments supplied.")

    if not promo.get("hook"):
        issues.append("Hook description is missing.")

    if not promo.get("cliffhanger"):
        issues.append("Cliffhanger description is missing.")

    method = promo.get("evaluation_method", "")
    if isinstance(method, str) and method.startswith("heuristic"):
        issues.append("Heuristic result requires human/editor validation.")

    return issues


def quality_summary(promos: list[dict]) -> dict:
    """Summarize evaluated promos and identify items needing review."""
    if not isinstance(promos, list):
        raise TypeError("Promos must be supplied as a list.")

    methods = {
        promo.get("evaluation_method", "unknown")
        for promo in promos
        if isinstance(promo, dict)
    }

    return {
        "promos_evaluated": len(promos),
        "duration_valid": sum(
            1 for promo in promos
            if isinstance(promo, dict)
            and _valid_duration(promo.get("duration_seconds"))
        ),
        "requires_human_review": sum(
            1 for promo in promos if validate_promo(promo)
        ),
        "method_counts": {
            method: sum(
                1 for promo in promos
                if isinstance(promo, dict)
                and promo.get("evaluation_method", "unknown") == method
            )
            for method in sorted(methods)
        },
    }
