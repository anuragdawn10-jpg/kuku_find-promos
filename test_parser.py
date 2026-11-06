from parser import parse_script, to_seconds

SAMPLE = """EPISODE NUMBER: Episode 7
EPISODE LOGLINE: A test logline.
CONTINUITY NOTES: A test note.
SCENE 01
Scene heading: INT. ROOM – DAY

**CAMERA:**
Start: (00:00.00) | End: (00:03.00)
A close-up of the door.

**HERO (Angry):**
Start: (00:03.00) | End: (00:05.50)
"Get out!"
"""

def test_timestamp_conversion():
    assert to_seconds("01:02.50") == 62.5

def test_parse_episode_and_events():
    ep = parse_script(SAMPLE, "episode-007-test.txt")
    assert ep.episode == 7
    assert ep.logline == "A test logline."
    assert len(ep.events) == 2
    assert ep.events[1].kind == "dialogue"
    assert ep.events[1].speaker == "HERO"
    assert ep.events[1].text == '"Get out!"'
