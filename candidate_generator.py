"""Generate continuous promo windows from parsed screenplay episodes."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from parser import Episode


def _event_dict(event: Any) -> dict:
    """Return an event as a plain dictionary without modifying the source."""
    if is_dataclass(event):
        return asdict(event)
    if isinstance(event, dict):
        return dict(event)
    raise TypeError("Episode events must be dataclasses or dictionaries.")


def _duration_options(
    min_duration: float,
    max_duration: float,
    step: float,
) -> list[float]:
    """Build descending duration choices and always include the minimum."""
    durations = []
    duration = max_duration

    while duration >= min_duration:
        durations.append(round(duration, 2))
        duration -= step

    if not durations or abs(durations[-1] - min_duration) > 1e-9:
        durations.append(round(min_duration, 2))

    return durations


def generate_candidates(
    episodes: list[Episode],
    min_duration: float = 20,
    max_duration: float = 60,
    step: float = 5,
) -> list[dict]:
    """Generate valid, overlapping continuous windows for each episode.

    Windows begin at the first event's start and advance by ``step`` seconds.
    A window is included only when it fits inside the episode's event timeline
    and intersects at least one event.
    """
    if min_duration <= 0 or max_duration < min_duration or step <= 0:
        raise ValueError("Invalid duration or step configuration.")

    durations = _duration_options(min_duration, max_duration, step)
    candidates = []

    for episode in episodes:
        if not episode.events:
            continue

        events = [_event_dict(event) for event in episode.events]
        valid_events = [
            event for event in events
            if event.get("start") is not None and event.get("end") is not None
        ]
        if not valid_events:
            continue

        timeline_start = min(float(event["start"]) for event in valid_events)
        timeline_end = max(float(event["end"]) for event in valid_events)

        start = timeline_start
        while start + min_duration <= timeline_end + 1e-9:
            for duration in durations:
                end = start + duration
                if end > timeline_end + 1e-9:
                    continue

                contained = [
                    event for event in valid_events
                    if float(event["end"]) > start and float(event["start"]) < end
                ]
                if not contained:
                    continue

                start_seconds = round(start, 2)
                end_seconds = round(end, 2)
                candidates.append({
                    "candidate_id": (
                        f"E{episode.episode:03d}_"
                        f"{int(round(start_seconds * 100)):06d}_"
                        f"{int(round(end_seconds * 100)):06d}"
                    ),
                    "episode": episode.episode,
                    "segments": [{
                        "start_seconds": start_seconds,
                        "end_seconds": end_seconds,
                        "start": seconds_to_label(start_seconds),
                        "end": seconds_to_label(end_seconds),
                    }],
                    "duration_seconds": round(duration, 2),
                    "logline": episode.logline,
                    "continuity": episode.continuity,
                    "events": contained,
                    "transcript": build_transcript(contained),
                })

            start += step

    # Preserve generation order while removing any duplicate windows.
    unique = {}
    for candidate in candidates:
        segment = candidate["segments"][0]
        key = (
            candidate["episode"],
            segment["start_seconds"],
            segment["end_seconds"],
        )
        unique.setdefault(key, candidate)

    return list(unique.values())


def seconds_to_label(value: float) -> str:
    """Format seconds as MM:SS.cc."""
    if value < 0:
        raise ValueError("Timestamp seconds cannot be negative.")

    total_centiseconds = int(round(value * 100))
    minutes, remainder = divmod(total_centiseconds, 6000)
    seconds, centiseconds = divmod(remainder, 100)
    return f"{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def build_transcript(events: list[dict]) -> str:
    """Format event records into a readable timestamped transcript."""
    lines = []
    for event in events:
        label = event.get("speaker") or str(event.get("kind") or "event").upper()
        start = event.get("start_label", "")
        end = event.get("end_label", "")
        text = str(event.get("text", "")).strip()
        lines.append(f"[{start}-{end}] {label}: {text}")
    return "\n".join(lines)(lines)
