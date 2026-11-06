"""Rank candidates and serialize final promo recommendations."""
from __future__ import annotations
from promo_scorer import evaluate

def rank_candidates(candidates: list[dict], use_llm: bool = False,
                    top_n: int | None = None) -> list[dict]:
    ranked = []
    for candidate in candidates:
        duration = float(candidate["duration_seconds"])
        if not 20 <= duration <= 60:
            continue
        result = evaluate(candidate, use_llm=use_llm)
        item = {k: v for k, v in candidate.items()
                if k not in ("events", "transcript")}
        item.update(result)
        item["segments"] = candidate["segments"]
        item["episode"] = candidate["episode"]
        item["candidate_id"] = candidate["candidate_id"]
        item["duration_seconds"] = duration
        ranked.append(item)
    ranked.sort(key=lambda x: x["total_score"], reverse=True)
    for i, item in enumerate(ranked, 1):
        item["rank"] = i
    return ranked[:top_n] if top_n else ranked
