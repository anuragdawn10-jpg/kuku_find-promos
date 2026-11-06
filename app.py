from __future__ import annotations
import json, os, tempfile
from pathlib import Path
import pandas as pd
import streamlit as st
from parser import parse_zip
from candidate_generator import generate_candidates
from ranker import rank_candidates
from evaluator import quality_summary

st.set_page_config(page_title="Kuku Promo Finder", page_icon="🎬", layout="wide")
st.title("🎬 Kuku Promo Finder")
st.caption("Screenplay-based promo discovery • 20–60 second clips")

with st.sidebar:
    st.header("Settings")
    use_llm = st.checkbox("Use Groq LLM evaluation", value=False,
                          help="Requires GROQ_API_KEY in your environment.")
    top_n = st.number_input("Promos to display", min_value=5, max_value=100,
                            value=20, step=5)
    st.info("The baseline heuristic works without an API key. Review all suggested clips manually.")

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
            with st.spinner("Generating candidates and evaluating them..."):
                candidates = generate_candidates(episodes)
                ranked = rank_candidates(candidates, use_llm=use_llm, top_n=int(top_n))
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
    st.caption(f"{st.session_state['candidate_count']} windows generated; showing top {len(ranked)}.")
    st.json(quality_summary(ranked))
    rows = []
    for promo in ranked:
        rows.append({
            "Rank": promo["rank"], "Episode": promo["episode"],
            "Start": promo["segments"][0]["start"], "End": promo["segments"][0]["end"],
            "Duration (s)": promo["duration_seconds"], "Score": promo["total_score"],
            "Method": promo["evaluation_method"]
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    for promo in ranked:
        with st.expander(f"#{promo['rank']} • Episode {promo['episode']} • Score {promo['total_score']}"):
            st.write(f"**Timestamp:** {promo['segments'][0]['start']} – {promo['segments'][0]['end']}")
            st.write(f"**Duration:** {promo['duration_seconds']} seconds")
            st.write(f"**Hook:** {promo['hook']}")
            st.write(f"**Cliffhanger:** {promo['cliffhanger']}")
            st.write(f"**Why it works:** {promo['why_it_works']}")
            st.write("**Scores:**", promo["scores"])
            st.write("**Review flags:**", promo.get("risk_flags", []))
    st.download_button("Download ranked_promos.json",
        json.dumps(ranked, indent=2, ensure_ascii=False),
        file_name="ranked_promos.json", mime="application/json")
    st.download_button("Download ranked_promos.csv",
        pd.DataFrame(rows).to_csv(index=False),
        file_name="ranked_promos.csv", mime="text/csv")
else:
    st.markdown("Upload the supplied ZIP, then select **Find and rank promos**.")
    st.warning("The app analyzes screenplay text and timestamps. It cannot verify actual video/audio quality.")
