"""Parser for Kuku's timestamped screenplay text files."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import re
import zipfile

TIME_RE = re.compile(r"(\d{2}):(\d{2})\.(\d{2})")
EVENT_RE = re.compile(
    r"Start:\s*\((\d{2}:\d{2}\.\d{2})\)\s*\|\s*End:\s*\((\d{2}:\d{2}\.\d{2})\)\s*\n(.*?)(?=\n\n|\Z)",
    re.S,
)
EP_RE = re.compile(r"EPISODE NUMBER:\s*Episode\s+(\d+)", re.I)
LOG_RE = re.compile(r"EPISODE LOGLINE:\s*(.*)", re.I)
CONT_RE = re.compile(r"CONTINUITY NOTES:\s*(.*)", re.I)
SCENE_RE = re.compile(r"^SCENE\s+(\d+)", re.M)

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
    m = TIME_RE.fullmatch(label.strip())
    if not m:
        raise ValueError(f"Invalid timestamp: {label}")
    minutes, seconds, centiseconds = map(int, m.groups())
    return minutes * 60 + seconds + centiseconds / 100

def parse_script(text: str, filename: str = "unknown.txt") -> Episode:
    ep_match = EP_RE.search(text)
    if not ep_match:
        # Filename convention: episode-001-...
        name_match = re.search(r"episode-(\d+)", filename, re.I)
        if not name_match:
            raise ValueError(f"Could not identify episode number in {filename}")
        episode_no = int(name_match.group(1))
    else:
        episode_no = int(ep_match.group(1))

    logline = (LOG_RE.search(text).group(1).strip()
               if LOG_RE.search(text) else "")
    continuity = (CONT_RE.search(text).group(1).strip()
                  if CONT_RE.search(text) else "")

    events: list[Event] = []
    current_scene = None
    lines = text.splitlines()
    # Parse blocks after Start/End lines; capture until the next blank line.
    i = 0
    while i < len(lines):
        scene_match = re.match(r"SCENE\s+(\d+)", lines[i].strip())
        if scene_match:
            current_scene = int(scene_match.group(1))
        m = re.search(r"Start:\s*\((\d{2}:\d{2}\.\d{2})\)\s*\|\s*End:\s*\((\d{2}:\d{2}\.\d{2})\)", lines[i])
        if m:
            start_label, end_label = m.groups()
            body_lines = []
            j = i + 1
            while j < len(lines) and lines[j].strip():
                body_lines.append(lines[j].strip())
                j += 1
            body = " ".join(body_lines).strip()
            # Find the nearest preceding category/speaker heading.
            heading = ""
            for k in range(i - 1, max(-1, i - 5), -1):
                candidate = lines[k].strip()
                if candidate.startswith("**") and candidate.endswith("**"):
                    heading = candidate.strip("*").strip()
                    break
                if re.match(r"^[A-Z][A-Z0-9 '’.-]+(?:\s*\([^)]*\))?:$", candidate):
                    heading = candidate.rstrip(":")
                    break
            if heading.upper().startswith("CAMERA"):
                kind, speaker = "camera", ""
            elif heading.upper().startswith("ACTION"):
                kind, speaker = "action", ""
            elif heading.upper().startswith("SOUND"):
                kind, speaker = "sound", ""
            elif heading:
                kind, speaker = "dialogue", re.sub(r"\s*\([^)]*\)", "", heading).strip()
            else:
                kind, speaker = "other", ""
            if body:
                try:
                    start_s, end_s = to_seconds(start_label), to_seconds(end_label)
                    if end_s >= start_s:
                        events.append(Event(episode_no, current_scene, kind, speaker,
                                            start_s, end_s, body, start_label, end_label))
                except ValueError:
                    pass
            i = j
        else:
            i += 1
    events.sort(key=lambda e: (e.start, e.end, e.kind))
    return Episode(episode_no, Path(filename).name, logline, continuity, events)

def parse_zip(zip_path: str | Path) -> list[Episode]:
    episodes = []
    with zipfile.ZipFile(zip_path) as zf:
        names = sorted(n for n in zf.namelist() if n.lower().endswith(".txt"))
        if not names:
            raise ValueError("ZIP contains no .txt screenplay files.")
        for name in names:
            raw = zf.read(name).decode("utf-8", errors="replace")
            episodes.append(parse_script(raw, name))
    return sorted(episodes, key=lambda e: e.episode)

def episode_to_dict(ep: Episode) -> dict:
    return {
        "episode": ep.episode, "filename": ep.filename,
        "logline": ep.logline, "continuity": ep.continuity,
        "events": [asdict(e) for e in ep.events]
    }
