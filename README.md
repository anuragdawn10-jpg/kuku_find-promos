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
