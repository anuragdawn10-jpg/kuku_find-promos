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
        help="All windows get quick heuristic scores; Groq is used only for the top candidates selected below.",
    )
    groq_limit = st.number_input(
        "Number of top candidates to evaluate with Groq",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
        disabled=not use_llm,
        help="Groq first evaluates the heuristic-ranked candidates, then the final list is re-ranked using the Groq scores.",
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
                    progress = st.progress(0, text="Scoring candidate windows...")
                    status = st.empty()

                    def update_progress(done: int, total: int) -> None:
                        progress.progress(
                            done / total,
                            text=f"Groq evaluation {done}/{total}",
                        )
                        status.caption(
                            f"Evaluating {done} of {total} selected candidates with Groq."
                        )

                    with st.spinner("Ranking promos; Groq is called only for the selected top candidates..." if use_llm else "Scoring and ranking promos..."):
                        ranked = rank_candidates(
                            candidates,
                            use_llm=use_llm,
                            top_n=int(top_n),
                            llm_limit=int(groq_limit),
                            progress_callback=update_progress if use_llm else None,
                        )
                    progress.empty()
                    status.empty()
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

    groq_count = sum(
        str(promo.get("evaluation_method", "")).startswith("llm:")
        for promo in ranked
    )
    fallback_count = sum(
        promo.get("evaluation_method") == "heuristic_fallback" for promo in ranked
    )
    if groq_count:
        st.success(f"Groq successfully evaluated {groq_count} displayed promo(s).")
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
        "video/audio quality. Enabling Groq sends selected screenplay excerpts to the Groq API."
    )
