"""Generate continuous 20–60 second candidate promo windows."""
from __future__ import annotations
from dataclasses import asdict
from parser import Episode, Event

def generate_candidates(episodes: list[Episode], min_duration: float = 20,
                        max_duration: float = 60, step: float = 5) -> list[dict]:
    if min_duration <= 0 or max_duration < min_duration or step <= 0:
        raise ValueError("Invalid duration or step configuration.")
    candidates = []
    for ep in episodes:
        if not ep.events:
            continue
        episode_end = max(e.end for e in ep.events)
        start = 0.0
        while start + min_duration <= episode_end:
            # Try longer windows first, then shorter ones.
            for duration in (max_duration, 50, 45, 40, 35, 30, 25, min_duration):
                if duration < min_duration or duration > max_duration:
                    continue
                end = start + duration
                if end > episode_end + 1e-6:
                    continue
                contained = [e for e in ep.events if e.end > start and e.start < end]
                if not contained:
                    continue
                candidates.append({
                    "candidate_id": f"E{ep.episode:03d}_{int(start*100):06d}_{int(end*100):06d}",
                    "episode": ep.episode,
                    "segments": [{"start_seconds": round(start, 2),
                                  "end_seconds": round(end, 2),
                                  "start": seconds_to_label(start),
                                  "end": seconds_to_label(end)}],
                    "duration_seconds": round(duration, 2),
                    "logline": ep.logline,
                    "continuity": ep.continuity,
                    "events": [asdict(e) for e in contained],
                    "transcript": build_transcript(contained),
                })
            start += step
    # Remove duplicate candidates (possible when max/min duration values overlap).
    unique = {}
    for c in candidates:
        key = (c["episode"], c["segments"][0]["start_seconds"],
               c["segments"][0]["end_seconds"])
        unique[key] = c
    return list(unique.values())

def seconds_to_label(value: float) -> str:
    total_cs = round(value * 100)
    minutes, remainder = divmod(total_cs, 6000)
    seconds, centiseconds = divmod(remainder, 100)
    return f"{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

def build_transcript(events: list[dict]) -> str:
    lines = []
    for e in events:
        label = e.get("speaker") or e.get("kind", "event").upper()
        lines.append(f'[{e["start_label"]}-{e["end_label"]}] {label}: {e["text"]}')
    return "\n".join(lines)
