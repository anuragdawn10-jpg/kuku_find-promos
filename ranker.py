"""Rank candidates and use Groq on a bounded top subset."""
from __future__ import annotations

from collections.abc import Callable

from promo_scorer import evaluate

ProgressCallback = Callable[[int, int], None]


def rank_candidates(
    candidates: list[dict],
    use_llm: bool = False,
    top_n: int | None = None,
    llm_limit: int = 5,
    progress_callback: ProgressCallback | None = None,
) -> list[dict]:
    """Score all eligible windows heuristically, then optionally call Groq only
    for the top ``llm_limit`` candidates from that initial ranking.

    This bounds network requests, so enabling Groq doesn't make one API call
    for every overlapping window. Groq-scored candidates are merged back into
    the ranking; all other candidates retain their heuristic evaluation.
    """
    eligible = [
        candidate for candidate in candidates
        if 20 <= float(candidate["duration_seconds"]) <= 60
    ]

    ranked: list[dict] = []
    for candidate in eligible:
        result = evaluate(candidate, use_llm=False)
        item = {key: value for key, value in candidate.items()
                if key not in ("events", "transcript")}
        item.update(result)
        item["segments"] = candidate["segments"]
        item["episode"] = candidate["episode"]
        item["candidate_id"] = candidate["candidate_id"]
        item["duration_seconds"] = float(candidate["duration_seconds"])
        ranked.append(item)

    ranked.sort(key=lambda item: item["total_score"], reverse=True)

    if use_llm and ranked:
        count = max(0, min(int(llm_limit), len(ranked)))
        selected = ranked[:count]
        candidate_by_id = {candidate["candidate_id"]: candidate for candidate in eligible}
        total = len(selected)
        for index, item in enumerate(selected, start=1):
            # evaluate() catches Groq errors and returns heuristic_fallback.
            item.update(evaluate(candidate_by_id[item["candidate_id"]], use_llm=True))
            if progress_callback is not None:
                progress_callback(index, total)

    ranked.sort(key=lambda item: item["total_score"], reverse=True)
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index

    return ranked[:top_n] if top_n else ranked
