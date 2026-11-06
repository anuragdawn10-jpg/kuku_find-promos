# Kuku Promo Finder — Problem 1

A small, rerunnable prototype that parses timestamped screenplay text, generates continuous 20–60 second candidate windows, evaluates them, and ranks them for editor review.

## Important assignment constraints

- This repository implements **Problem 1: Find the Promos (Ads)**.
- The supplied Kuku screenplay pack is confidential. The assignment says it is shared only for this assignment and must not be published or shared. **Do not commit the ZIP or extracted scripts to GitHub.** Keep the input locally.
- The application identifies moments and timestamps only. It does not edit video, add music/overlays, or verify actual footage/audio.
- Heuristic scores are a baseline, not ground truth. Human/editor review is required.
- The assignment asks for promos of 20–60 seconds, usually continuous but potentially composed of multiple segments. This first prototype generates continuous windows only.

## Features

1. Reads `.txt` files from a screenplay ZIP.
2. Extracts episode number, logline, continuity notes, scene IDs, event type, speaker, text, and timestamps.
3. Generates overlapping continuous candidate windows.
4. Scores hook, cliffhanger, emotion, standalone clarity, and coherence.
5. Ranks candidates and exports JSON/CSV.
6. Offers optional Groq LLM evaluation; falls back to the deterministic heuristic when unavailable.
7. Includes automated parser, duration, and quality tests.

## Setup

Python 3.10+ recommended.

```bash
git clone <your-repository-url>
cd kuku-promo-finder
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.venv\\Scripts\\Activate.ps1
```

**macOS/Linux**
```bash
source .venv/bin/activate
```

Install packages:

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Upload the original screenplay ZIP through the app. The app parses the files locally in memory and produces ranked recommendations. Download the JSON/CSV outputs from the dashboard.

## Optional LLM evaluation

The heuristic baseline works without a key. To use Groq:

**Windows PowerShell**
```powershell
$env:GROQ_API_KEY="your-key"
$env:GROQ_MODEL="llama-3.3-70b-versatile"
streamlit run app.py
```

**macOS/Linux**
```bash
export GROQ_API_KEY="your-key"
export GROQ_MODEL="llama-3.3-70b-versatile"
streamlit run app.py
```

### Streamlit Community Cloud

In your app's **Settings → Secrets**, add:

```toml
GROQ_API_KEY = "your-groq-api-key"
GROQ_MODEL = "llama-3.3-70b-versatile"
```

Save the secrets and redeploy/restart the app. The evaluator reads credentials from Streamlit secrets or environment variables. Then enable **Use Groq LLM evaluation** in the sidebar. If the key is missing or a Groq request fails, the app continues with heuristic scoring. Do not commit `.streamlit/secrets.toml`, `.env`, or API keys.

Enabling Groq sends the screenplay excerpt to Groq for evaluation. Only use this with input you are permitted to share with that service.

## Tests

```bash
pytest -q
```

## Scoring

| Criterion | Weight |
|---|---:|
| Hook | 25% |
| Cliffhanger | 25% |
| Emotional impact | 20% |
| Standalone clarity | 20% |
| Narrative coherence | 10% |

Each score is 0–10. Weighted total is also on a 0–10 scale. Duration is a hard constraint, not a score.

## Output schema

Each ranked item contains:
- `rank`, `candidate_id`, `episode`
- `segments`: ordered start/end timestamps
- `duration_seconds`
- `scores`, `total_score`, `evaluation_method`
- `hook`, `cliffhanger`, `why_it_works`, `risk_flags`

The current version returns one continuous segment per candidate.

## Known limitations and honest quality checks

- It reads screenplay text, not video/audio. It cannot judge acting, visual clarity, music, shot quality, or actual editability.
- Keyword heuristics can miss subtle hooks and overrate dramatic words in weak scenes.
- The LLM may infer too much; the prompt instructs it to use only excerpt evidence, but human review remains necessary.
- The sliding-window generator is simple and can produce many overlapping candidates.
- It does not yet optimize multi-segment promos or deduplicate near-identical story beats across episodes.
- Review top-ranked and randomly sampled low-ranked clips. Record false positives/negatives and compare against editor selections.

## Suggested next improvements

1. Add human labels for the top 20 candidates and calculate precision@K.
2. Add semantic duplicate detection across overlapping windows.
3. Add multi-segment promo assembly with total duration validation.
4. Add a reviewer feedback CSV and use it to tune weights.
5. Add actual video linking only if matching source footage and timecode conventions are available.

## Repository contents

```text
app.py
parser.py
candidate_generator.py
promo_scorer.py
ranker.py
evaluator.py
tests/
solution_document.md
requirements.txt
```
