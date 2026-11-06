# Test results — Kuku Promo Finder

Run: 2026-11-06 16:55 (server time, UTC), Python 3.13.18

**Summary:** 20/20 passed, 0 failed. `pytest`: 6 passed in 0.01s.

`PASS*` = passed against a **synthetic** 50-episode ZIP I generated in the same timestamp format. The real Kuku screenplay pack was not available, so TC01 and TC20 still need a run on the real files.

| ID | Condition | Expected | Result | Evidence |
|---|---|---|---|---|
| TC01 | Valid ZIP with 50 `.txt` files | All episode files parsed | **PASS*** | Parsed 50 synthetic episodes, 700 events. *Synthetic ZIP, not the real Kuku pack. |
| TC02 | ZIP with no `.txt` files | Clear `ValueError` | **PASS** | ValueError: ZIP contains no .txt screenplay files. |
| TC03 | Episode number in header | Correct episode number | **PASS** | episode=7 |
| TC04 | Episode number absent, filename has episode-007 | Fallback to filename | **PASS** | episode=7 from filename |
| TC05 | Timestamp `01:02.50` | 62.5 seconds | **PASS** | 62.5 |
| TC06 | Invalid timestamp | Raises `ValueError` | **PASS** | to_seconds raised ValueError for all invalid inputs; accepted: []. Note: parse_script silently drops events with invalid timestamps (events parsed=0) instead of raising. |
| TC07 | Camera/action/dialogue event blocks | Correct kind and text | **PASS** | kinds=['camera', 'dialogue', 'dialogue', 'dialogue', 'camera'] |
| TC08 | Empty episode | No candidates | **PASS** | no candidates |
| TC09 | 70-second timeline | Only 20–60 s windows | **PASS** | 63 windows, durations=[20, 25, 30, 35, 40, 45, 50, 55, 60] |
| TC10 | Candidate is 19 s | Rejected | **PASS** | ranker kept=0, validator flagged=True |
| TC11 | Candidate is 20 s | Accepted | **PASS** | ranker kept=1, validator flagged=False |
| TC12 | Candidate is 60 s | Accepted | **PASS** | ranker kept=1, validator flagged=False |
| TC13 | Candidate is 61 s | Rejected | **PASS** | ranker kept=0, validator flagged=True |
| TC14 | Strong opening dialogue | Hook evidence from first 3 s | **PASS** | hook evidence='Wait! Why are you marrying him? Stop!', hook score=10 |
| TC15 | Unresolved final line | Cliffhanger evidence from last 5 s | **PASS** | cliffhanger evidence="Will you accept? Please, you don't know the truth.", score=10 |
| TC16 | No API key, LLM disabled | Heuristic runs | **PASS** | method=heuristic, total=4.15 |
| TC17 | LLM enabled without key | Heuristic fallback + risk flag | **PASS** | method=heuristic_fallback, flag=Groq unavailable; heuristic fallback used: RuntimeError: GROQ_API_KEY  |
| TC18 | LLM malformed/invalid response | Fallback to heuristic | **PASS** | Simulated: non-JSON -> heuristic_fallback; score out of range -> heuristic_fallback; missing scores -> heuristic_fallback; empty -> heuristic_fallback; API exception -> heuristic_fallback |
| TC19 | Many overlapping windows | Score-descending | **PASS** | 189 windows from 3 synthetic episodes; score-descending=True. With mocked Groq on top 3: Groq-scored ranked first and remainder score-descending=True. |
| TC20 | Full input pack exports | JSON/CSV contain ranked results | **PASS*** | JSON has 20 ranked items, CSV has 20 rows. *Synthetic ZIP; app's download buttons themselves not clicked. |

## App check (TC16/TC17 in the UI)

**Not run.** Streamlit is not installed in this sandbox, so the UI was not exercised. TC16/TC17 above were run against the scoring functions directly. Please click through the app once with and without `GROQ_API_KEY` set.

## Findings

- TC06: `to_seconds` rejects bad timestamps, but `parse_script` swallows the error and drops that event with no warning. A malformed timestamp in a real script would silently remove dialogue. Consider raising or collecting warnings.
- Heuristic scores count each keyword once per window, so repeating a word does not raise the score. This follows from the code (`_hits` counts distinct terms); I did not measure how often windows tie.
- Groq results here are **mocked**. No real Groq API call was made, so TC18 shows the fallback logic works but not how the real model behaves.

## Not run: manual content review cases

These need the real episodes and a human reviewer (cathedral betrayal in Ep 1, Gerald reveal, Ep 3 stranger/proposal, cross-episode context, answered-question endings). They are **not** marked as passed. Use the human review sheet in `TEST_CASES.md` once the real pack is loaded.
