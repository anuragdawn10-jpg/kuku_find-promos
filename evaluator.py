"""Small quality checks and human-review worksheet generation."""
from __future__ import annotations

def validate_promo(promo: dict) -> list[str]:
    issues = []
    duration = promo.get("duration_seconds")
    if duration is None or not 20 <= float(duration) <= 60:
        issues.append("Duration is outside the required 20–60 second range.")
    if not promo.get("segments"):
        issues.append("No segments supplied.")
    if not promo.get("hook"):
        issues.append("Hook description is missing.")
    if not promo.get("cliffhanger"):
        issues.append("Cliffhanger description is missing.")
    if promo.get("evaluation_method", "").startswith("heuristic"):
        issues.append("Heuristic result requires human/editor validation.")
    return issues

def quality_summary(promos: list[dict]) -> dict:
    return {
        "promos_evaluated": len(promos),
        "duration_valid": sum(1 for p in promos if 20 <= p.get("duration_seconds", 0) <= 60),
        "requires_human_review": sum(1 for p in promos if validate_promo(p)),
        "method_counts": {
            method: sum(1 for p in promos if p.get("evaluation_method") == method)
            for method in sorted({p.get("evaluation_method", "unknown") for p in promos})
        }
    }
