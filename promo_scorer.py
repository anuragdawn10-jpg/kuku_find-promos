"""Heuristic baseline scorer plus optional Groq LLM evaluator.

The heuristic is a reproducible baseline, not a substitute for editor review.
Set GROQ_API_KEY and GROQ_MODEL to enable LLM-assisted evaluation.
"""
from __future__ import annotations
import json, os, re

WEIGHTS = {"hook": .25, "cliffhanger": .25, "emotion": .20,
           "standalone": .20, "coherence": .10}

HOOK_TERMS = ["what", "why", "no", "never", "stop", "don't", "you should",
              "look", "wait", "because", "marrying", "betray", "secret"]
CLIFF_TERMS = ["will you", "accept", "who are you", "what happened", "please",
               "I swear", "you don't know", "the truth", "marry", "choose"]
EMOTION_TERMS = ["cry", "tears", "heartbroken", "shocked", "furious", "love",
                 "hate", "betray", "desperate", "screaming", "begging"]

def _hits(text: str, terms: list[str]) -> int:
    low = text.lower()
    return sum(1 for term in terms if term in low)

def heuristic_evaluate(candidate: dict) -> dict:
    events = candidate.get("events", [])
    transcript = candidate.get("transcript", "")
    first3 = [e for e in events if e["start"] < candidate["segments"][0]["start_seconds"] + 3]
    last5_start = candidate["segments"][0]["end_seconds"] - 5
    last5 = [e for e in events if e["end"] > last5_start]
    hook_text = " ".join(e["text"] for e in first3)
    ending_text = " ".join(e["text"] for e in last5)
    hook = min(10, 3 + 1.5 * _hits(hook_text, HOOK_TERMS) + (2 if first3 else 0))
    cliff = min(10, 2 + 1.6 * _hits(ending_text, CLIFF_TERMS) + (2 if "?" in ending_text else 0))
    emotion = min(10, 2 + 1.4 * _hits(transcript, EMOTION_TERMS))
    dialogue_count = sum(1 for e in events if e.get("kind") == "dialogue")
    standalone = min(10, 4 + (2 if candidate.get("logline") else 0) +
                     (2 if dialogue_count >= 3 else 0))
    coherence = min(10, 4 + (2 if events else 0) +
                    (2 if candidate["duration_seconds"] >= 25 else 0))
    scores = {"hook": round(hook, 1), "cliffhanger": round(cliff, 1),
              "emotion": round(emotion, 1), "standalone": round(standalone, 1),
              "coherence": round(coherence, 1)}
    total = round(sum(scores[k] * WEIGHTS[k] for k in WEIGHTS), 2)
    return {
        "scores": scores, "total_score": total, "evaluation_method": "heuristic",
        "hook": hook_text[:300] or "No dialogue/action detected in first 3 seconds.",
        "cliffhanger": ending_text[:300] or "No clear ending event detected.",
        "why_it_works": "Baseline keyword and structure score; editor review required.",
        "risk_flags": ["Heuristic scores may overrate keyword matches."]
    }

def llm_evaluate(candidate: dict, model: str | None = None) -> dict:
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
coherence; each integer 0-10), hook (brief exact evidence/description),
cliffhanger (brief exact evidence/description), why_it_works (one sentence),
risk_flags (array of strings). Be conservative and flag missing context.
Episode: {candidate['episode']}
Logline: {candidate.get('logline','')}
Clip: {candidate['segments']}
Transcript:
{candidate['transcript'][:12000]}
"""
    response = Groq(api_key=api_key).chat.completions.create(
        model=model, temperature=0.1,
        messages=[{"role":"user","content":prompt}],
        response_format={"type":"json_object"}
    )
    result = json.loads(response.choices[0].message.content)
    result["evaluation_method"] = f"llm:{model}"
    scores = result.get("scores", {})
    for key in WEIGHTS:
        scores[key] = max(0, min(10, float(scores.get(key, 0))))
    result["total_score"] = round(sum(scores[k] * WEIGHTS[k] for k in WEIGHTS), 2)
    result["scores"] = scores
    return result

def evaluate(candidate: dict, use_llm: bool = False) -> dict:
    if use_llm:
        try:
            return llm_evaluate(candidate)
        except Exception as exc:
            result = heuristic_evaluate(candidate)
            result["risk_flags"].append(f"LLM unavailable; heuristic fallback used: {exc}")
            result["evaluation_method"] = "heuristic_fallback"
            return result
    return heuristic_evaluate(candidate)
