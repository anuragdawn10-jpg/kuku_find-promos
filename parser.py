"""Parser for timestamped screenplay text files."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import zipfile


TIME_RE = re.compile(r"(\d{2,}):(\d{2})\.(\d{2})")
TIMESTAMP_LINE_RE = re.compile(
    r"Start:\s*\((\d{2,}:\d{2}\.\d{2})\)\s*\|\s*"
    r"End:\s*\((\d{2,}:\d{2}\.\d{2})\)",
    re.IGNORECASE,
)
EP_RE = re.compile(r"EPISODE NUMBER:\s*(?:Episode\s*)?(\d+)", re.IGNORECASE)
LOG_RE = re.compile(r"EPISODE LOGLINE:\s*(.*)", re.IGNORECASE)
CONT_RE = re.compile(r"CONTINUITY NOTES:\s*(.*)", re.IGNORECASE)
SCENE_RE = re.compile(r"^SCENE\s+(\d+)\b", re.IGNORECASE)


@dataclass
class Event:
    episode: int
    scene: int | None
    kind: str
    speaker: str
    start: float
    end: float
    text: str
    start_label: str
    end_label: str


@dataclass
class Episode:
    episode: int
    filename: str
    logline: str
    continuity: str
    events: list[Event]


def to_seconds(label: str) -> float:
    """Convert a MM:SS.cc timestamp to seconds."""
    match = TIME_RE.fullmatch(label.strip())
    if not match:
        raise ValueError(f"Invalid timestamp: {label}")

    minutes, seconds, centiseconds = map(int, match.groups())
    if seconds >= 60 or centiseconds >= 100:
        raise ValueError(f"Invalid timestamp: {label}")

    return minutes * 60 + seconds + centiseconds / 100


def _header_value(pattern: re.Pattern, text: str) -> str:
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _classify_heading(heading: str) -> tuple[str, str]:
    heading = heading.strip().strip("*").strip().rstrip(":").strip()
    upper_heading = heading.upper()

    for label, kind in (
        ("CAMERA", "camera"),
        ("ACTION", "action"),
        ("SOUND", "sound"),
    ):
        if upper_heading.startswith(label):
            return kind, ""

    if heading:
        speaker = re.sub(r"\s*\([^)]*\)", "", heading).strip()
        return "dialogue", speaker

    return "other", ""


def _find_heading(lines: list[str], event_line: int) -> str:
    """Find a nearby category/speaker heading above a timestamp."""
    for index in range(event_line - 1, max(-1, event_line - 6), -1):
        candidate = lines[index].strip()
        if not candidate:
            continue

        if candidate.startswith("**") and candidate.endswith("**"):
            return candidate

        if re.match(r"^[A-Z][A-Z0-9 '’.-]*(?:\s*\([^)]*\))?:$", candidate):
            return candidate

        # Don't accidentally use a prior event's heading.
        if TIMESTAMP_LINE_RE.search(candidate):
            break

    return ""


def parse_script(text: str, filename: str = "unknown.txt") -> Episode:
    """Parse episode metadata and timestamped screenplay events."""
    if not isinstance(text, str):
        raise TypeError("Screenplay text must be a string.")

    episode_match = EP_RE.search(text)
    if episode_match:
        episode_number = int(episode_match.group(1))
    else:
        filename_match = re.search(r"episode-(\d+)", filename, re.IGNORECASE)
        if not filename_match:
            raise ValueError(f"Could not identify episode number in {filename}")
        episode_number = int(filename_match.group(1))

    logline = _header_value(LOG_RE, text)
    continuity = _header_value(CONT_RE, text)
    lines = text.splitlines()
    events = []
    current_scene = None
    index = 0

    while index < len(lines):
        scene_match = SCENE_RE.match(lines[index].strip())
        if scene_match:
            current_scene = int(scene_match.group(1))

        timestamp_match = TIMESTAMP_LINE_RE.search(lines[index])
        if not timestamp_match:
            index += 1
            continue

        start_label, end_label = timestamp_match.groups()
        body_lines = []
        body_index = index + 1

        # Capture the event body up to a blank line or the next event block.
        while body_index < len(lines):
            line = lines[body_index]
            if not line.strip() or TIMESTAMP_LINE_RE.search(line):
                break
            body_lines.append(line.strip())
            body_index += 1

        body = " ".join(line for line in body_lines if line).strip()
        heading = _find_heading(lines, index)
        kind, speaker = _classify_heading(heading)

        if body:
            try:
                start_seconds = to_seconds(start_label)
                end_seconds = to_seconds(end_label)
            except ValueError:
                start_seconds = end_seconds = -1

            if start_seconds >= 0 and end_seconds >= start_seconds:
                events.append(Event(
                    episode=episode_number,
                    scene=current_scene,
                    kind=kind,
                    speaker=speaker,
                    start=start_seconds,
                    end=end_seconds,
                    text=body,
                    start_label=start_label,
                    end_label=end_label,
                ))

        # If the next block immediately follows this one, process it next.
        index = body_index if body_index > index + 1 else index + 1

    events.sort(key=lambda event: (event.start, event.end, event.kind))
    return Episode(
        episode=episode_number,
        filename=Path(filename).name,
        logline=logline,
        continuity=continuity,
        events=events,
    )


def parse_zip(zip_path: str | Path) -> list[Episode]:
    """Parse all .txt screenplay files in a ZIP archive."""
    episodes = []

    with zipfile.ZipFile(zip_path) as archive:
        names = sorted(
            name for name in archive.namelist()
            if name.lower().endswith(".txt") and not name.endswith("/")
        )
        if not names:
            raise ValueError("ZIP contains no .txt screenplay files.")

        for name in names:
            raw_text = archive.read(name).decode("utf-8", errors="replace")
            episodes.append(parse_script(raw_text, name))

    return sorted(episodes, key=lambda episode: episode.episode)


def episode_to_dict(ep: Episode) -> dict:
    """Serialize an episode and its events into plain Python dictionaries."""
    return {
        "episode": ep.episode,
        "filename": ep.filename,
        "logline": ep.logline,
        "continuity": ep.continuity,
        "events": [asdict(event) for event in ep.events],
    }
