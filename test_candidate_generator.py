from parser import Event, Episode
from candidate_generator import generate_candidates

def test_generates_only_valid_duration_windows():
    events = [Event(1, 1, "dialogue", "A", 0, 70, "Help!", "00:00.00", "01:10.00")]
    ep = Episode(1, "episode-001.txt", "Logline", "", events)
    candidates = generate_candidates([ep], min_duration=20, max_duration=60, step=10)
    assert candidates
    assert all(20 <= c["duration_seconds"] <= 60 for c in candidates)

def test_empty_episode_has_no_candidates():
    ep = Episode(1, "empty.txt", "", "", [])
    assert generate_candidates([ep]) == []
