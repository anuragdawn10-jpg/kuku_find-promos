from __future__ import annotations

import json
import os
import tempfile

import pandas as pd
import streamlit as st

from candidate_generator import generate_candidates
from evaluator import quality_summary
from parser import parse_zip
from ranker import rank_candidates


def groq_configured() -> bool:
    """True if GROQ_API_KEY is set in env vars or Streamlit secrets."""
    if os.getenv("GROQ_API_KEY"):
        return True
    try:
        return bool(st.secrets.get("GROQ_API_KEY"))
    except Exception:
        return False


st.set_page_config(page_title="Kuku Promo Finder", page_icon="🎬", layout="wide")
st.title("🎬 Kuku Promo Finder")
st.caption("Screenplay-based promo discovery • 20–60 second clips")

with st.sidebar:
    st.header("Settings")
    key_ok = groq_configured()
    use_llm = st.checkbox(
        "Use Groq LLM evaluation",
        value=False,
        disabled=not key_ok,
        help="Runs Groq only on the top heuristic-ranked windows; the rest keep heuristic scores.",
    )
    llm_limit = st.slider(
        "Groq-evaluate top N windows", min_value=1, max_value=20, value=5,
        disabled=not (use_llm and key_ok),
    )
    if not key_ok:
        st.warning("GROQ_API_KEY not found. Add it to Streamlit secrets or env vars.")
    elif use_llm:
        st.caption(
            "The top windows are sent to Groq. Only use this with text you are "
            "permitted to share with that service."
        )
    else:
        st.info("Using the local heuristic evaluator only. No Groq calls are made.")
    top_n = st.number_input(
        "Promos to display", min_value=5, max_value=100, value=20, step=5
    )
    st.info("Heuristic scoring is a baseline. Review all suggested clips manually.")

uploaded = st.file_uploader("Upload the screenplay ZIP", type=["zip"])
if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(uploaded.getvalue())
        zip_path = tmp.name
    try:
        with st.spinner("Parsing screenplay episodes..."):
            episodes = parse_zip(zip_path)
        st.success(f"Parsed {len(episodes)} episode files.")
        col1, col2, col3 = st.columns(3)
        col1.metric("Episodes", len(episodes))
        col2.metric("Timestamped events", sum(len(e.events) for e in episodes))
        col3.metric("Episodes with events", sum(bool(e.events) for e in episodes))

        if st.button("Find and rank promos", type="primary"):
            try:
                with st.spinner("Generating promo windows..."):
                    candidates = generate_candidates(episodes)
                st.session_state["candidate_count"] = len(candidates)

                if not candidates:
                    st.warning(
                        "No eligible 20–60 second promo windows were found. "
                        "Check that the scripts contain valid timestamps spanning "
                        "at least 20 seconds."
                    )
                    st.session_state.pop("ranked", None)
                else:
                    progress = st.progress(0.0, text="Scoring and ranking promos...")

                    def _on_progress(done: int, total: int) -> None:
                        progress.progress(
                            done / total, text=f"Groq evaluated {done}/{total} windows"
                        )

                    ranked = rank_candidates(
                        candidates,
                        use_llm=use_llm,
                        top_n=int(top_n),
                        llm_limit=int(llm_limit),
                        progress_callback=_on_progress if use_llm else None,
                    )
                    progress.empty()
                    if use_llm:
                        failed = [
                            r for r in ranked
                            if r["evaluation_method"] == "heuristic_fallback"
                        ]
                        ok = sum(r["evaluation_method"].startswith("llm:") for r in ranked)
                        if failed:
                            st.warning(
                                f"Groq failed for {len(failed)} window(s); heuristic "
                                f"fallback used. First error: "
                                f"{failed[0]['risk_flags'][-1]}"
                            )
                        if ok:
                            st.success(f"{ok} window(s) scored by Groq.")
                    st.session_state["ranked"] = ranked
                    st.session_state["episodes"] = len(episodes)
                    st.session_state["events"] = sum(len(e.events) for e in episodes)
            except Exception as exc:
                st.error(f"Could not generate and rank promos: {exc}")
    except Exception as exc:
        st.error(f"Could not process ZIP: {exc}")
    finally:
        try:
            os.unlink(zip_path)
        except OSError:
            pass

if "ranked" in st.session_state:
    ranked = st.session_state["ranked"]
    st.subheader("Ranked promo candidates")
    st.caption(
        f"{st.session_state.get('candidate_count', len(ranked))} windows generated; "
        f"showing top {len(ranked)}."
    )

    st.json(quality_summary(ranked))
    rows = []
    for promo in ranked:
        rows.append({
            "Rank": promo["rank"],
            "Episode": promo["episode"],
            "Start": promo["segments"][0]["start"],
            "End": promo["segments"][0]["end"],
            "Duration (s)": promo["duration_seconds"],
            "Score": promo["total_score"],
            "Method": promo["evaluation_method"],
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    for promo in ranked:
        with st.expander(
            f"#{promo['rank']} • Episode {promo['episode']} • Score {promo['total_score']}"
        ):
            st.write(
                f"**Timestamp:** {promo['segments'][0]['start']} – "
                f"{promo['segments'][0]['end']}"
            )
            st.write(f"**Duration:** {promo['duration_seconds']} seconds")
            st.write(f"**Evaluation:** {promo['evaluation_method']}")
            st.write(f"**Hook:** {promo['hook']}")
            st.write(f"**Cliffhanger:** {promo['cliffhanger']}")
            st.write(f"**Why it works:** {promo['why_it_works']}")
            st.write("**Scores:**", promo["scores"])
            st.write("**Review flags:**", promo.get("risk_flags", []))

    st.download_button(
        "Download ranked_promos.json",
        json.dumps(ranked, indent=2, ensure_ascii=False),
        file_name="ranked_promos.json",
        mime="application/json",
    )
    st.download_button(
        "Download ranked_promos.csv",
        pd.DataFrame(rows).to_csv(index=False),
        file_name="ranked_promos.csv",
        mime="text/csv",
    )
else:
    st.markdown("Upload the supplied ZIP, then select **Find and rank promos**.")
    st.warning(
        "The app analyzes screenplay text and timestamps. It cannot verify actual "
        "video/audio quality."
    )
