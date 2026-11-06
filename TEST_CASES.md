# Test plan — Kuku Promo Finder

These are designed tests. A test is not marked as passed until it has actually been run.

| ID | Input / condition | Expected result | Automated coverage |
|---|---|---|---|
| TC01 | Valid ZIP with 50 `.txt` files | All episode files parsed | Run full ZIP manually |
| TC02 | ZIP with no `.txt` files | Clear `ValueError` | Parser behavior |
| TC03 | Episode number in header | Correct episode number | `test_parse_episode_and_events` |
| TC04 | Episode number absent but filename has episode-007 | Fallback to filename | Manual/extend test |
| TC05 | Timestamp `01:02.50` | Converts to 62.5 seconds | `test_timestamp_conversion` |
| TC06 | Invalid timestamp | Raises `ValueError` | Manual/extend test |
| TC07 | Camera/action/dialogue event blocks | Correct kind and text extraction | `test_parse_episode_and_events` |
| TC08 | Empty episode | No candidates | `test_empty_episode_has_no_candidates` |
| TC09 | 70-second timeline | Only windows from 20 through 60 seconds | `test_generates_only_valid_duration_windows` |
| TC10 | Candidate is 19 seconds | Rejected by ranker/validator | Manual/extend test |
| TC11 | Candidate is 20 seconds | Accepted by duration rule | Manual/extend test |
| TC12 | Candidate is 60 seconds | Accepted by duration rule | Manual/extend test |
| TC13 | Candidate is 61 seconds | Rejected | `test_flags_out_of_range_duration` |
| TC14 | Strong opening dialogue | Hook evidence should reflect opening 3 seconds | Inspect output |
| TC15 | Unresolved final line | Cliffhanger evidence should reflect last 5 seconds | Inspect output |
| TC16 | No API key, LLM disabled | Heuristic evaluator runs | Run app |
| TC17 | LLM enabled without key | Heuristic fallback and risk flag | Run app |
| TC18 | LLM returns malformed/invalid response | Fallback to heuristic | Simulate API error |
| TC19 | Many overlapping windows | Ranked list is score-descending | Inspect output |
| TC20 | Full input pack | JSON/CSV exports contain ranked results | Run full ZIP |

## Manual content review cases

Use these as reviewer prompts, not hard-coded expected truths:

- Episode 1: Does the betrayal at the cathedral create an understandable hook and unresolved emotional question?
- Episode 1: Does the line revealing that Gerald is marrying someone else work as a reveal?
- Episode 3: Does the stranger defending Juliana establish enough context for a new viewer?
- Episode 3: Does the proposal ending create a compelling unresolved question?
- Any episode: Does a candidate depend on context from an earlier episode?
- Any episode: Does the candidate end after the dramatic question has already been answered?

## Human review sheet

For each reviewed promo, record: candidate ID, reviewer, hook (0–5), cliffhanger (0–5), standalone clarity (0–5), timestamp correctness (yes/no), overall promo-worthy (yes/no), failure reason, notes.
