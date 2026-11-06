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


def _groq_api_key_configured() -> bool:
    """Check whether Groq credentials are available without displaying them."""
    if os.getenv("GROQ_API_KEY"):
        return True
    try:
        return bool(st.secrets.get("GROQ_API_KEY"))
    except Exception:
        # Streamlit secrets may not be configured in local development.
        return False


st.set_page_config(page_title="Kuku Promo Finder", page_icon="🎬", layout="wide")
st.title("🎬 Kuku Promo Finder")
st.caption("Screenplay-based promo discovery • 20–60 second clips")

groq_ready = _groq_api_key_configured()
with st.sidebar:
    st.header("Settings")
    if groq_ready:
        st.success("Groq API key configured")
    else:
        st.info("Groq is optional. Add GROQ_API_KEY in Streamlit Cloud → Settings → Secrets to enable it.")

    use_llm = st.checkbox(
        "Use Groq AI evaluation",
        value=False,
        disabled=not groq_ready,
        help="Groq evaluates promo candidates and contributes to their ranking. If a request fails, heuristic scoring is used instead.",
    )
    top_n = st.number_input(
        "Promos to display", min_value=5, max_value=100, value=20, step=5
    )
    st.info("Heuristic scoring is the default. Review all suggested clips manually.")

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
            with st.spinner(
                "Generating candidates and evaluating with Groq..."
                if use_llm
                else "Generating candidates and evaluating them..."
            ):
                candidates = generate_candidates(episodes)
                ranked = rank_candidates(
                    candidates, use_llm=use_llm, top_n=int(top_n)
                )
            st.session_state["ranked"] = ranked
            st.session_state["candidate_count"] = len(candidates)
            st.session_state["episodes"] = len(episodes)
            st.session_state["events"] = sum(len(e.events) for e in episodes)
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
        f"{st.session_state['candidate_count']} windows generated; "
        f"showing top {len(ranked)}."
    )

    fallback_count = sum(
        promo.get("evaluation_method") == "heuristic_fallback" for promo in ranked
    )
    if fallback_count:
        st.warning(
            f"Groq was unavailable for {fallback_count} displayed candidate(s); "
            "heuristic fallback scores were used. See review flags below."
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
        "video/audio quality. Enabling Groq sends screenplay excerpts to the Groq API."
    )
