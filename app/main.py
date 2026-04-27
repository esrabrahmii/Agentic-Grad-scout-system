"""Streamlit UI for grad-scout."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gradscout.models import SearchConstraints
from gradscout.utils.logging import configure_logging

configure_logging()

st.set_page_config(
    page_title="grad-scout",
    page_icon=":material/school:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("grad-scout")
st.caption("Find and rank graduate programs that match your profile — automatically.")

# ---------------------------------------------------------------------------
# Sidebar — search constraints
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Search Constraints")

    fields_input = st.text_input(
        "Fields of interest",
        value="machine learning, artificial intelligence",
        help="Comma-separated keywords, e.g. 'machine learning, NLP, data science'",
    )

    countries_input = st.text_input(
        "Countries (leave blank for all Europe)",
        value="Germany, Netherlands, France",
        help="Comma-separated country names",
    )

    level = st.radio("Degree level", ["masters", "phd", "both"], index=0)

    fee_option = st.radio(
        "Tuition budget",
        ["Free programs only", "Under €5,000/yr", "Under €10,000/yr", "No limit"],
        index=0,
    )
    fee_map = {
        "Free programs only": 0,
        "Under €5,000/yr": 5000,
        "Under €10,000/yr": 10_000,
        "No limit": None,
    }
    max_fees = fee_map[fee_option]

    start_year = st.selectbox("Start year", [2025, 2026, 2027], index=1)

    max_programs = st.slider(
        "Max programs to research",
        min_value=5,
        max_value=30,
        value=15,
        step=5,
        help="More programs = more thorough but slower (each requires a page visit)",
    )

    run_button = st.button("Search programs", type="primary", icon=":material/search:")

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------
if not run_button:
    st.info("Configure your search constraints in the sidebar, then click **Search programs**.")

    st.markdown("### How it works")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("**1. Discover**\nSearches mastersportal.eu with your filters")
    with col2:
        st.markdown("**2. Research**\nVisits each university page to extract requirements, fees & deadlines")
    with col3:
        st.markdown("**3. Score**\nRanks programs by how well they match your constraints")
    with col4:
        st.markdown("**4. Compare**\nOutputs a ranked table with direct application links")
    st.stop()

# ---------------------------------------------------------------------------
# Build constraints and run the graph
# ---------------------------------------------------------------------------
fields = [f.strip() for f in fields_input.split(",") if f.strip()]
countries = [c.strip() for c in countries_input.split(",") if c.strip()]

if not fields:
    st.error("Please enter at least one field of interest.")
    st.stop()

constraints = SearchConstraints(
    fields=fields,
    countries=countries,
    max_fees_eur_per_year=max_fees,
    level=level,
    start_year=start_year,
    max_programs=max_programs,
)

# Progress display
progress_placeholder = st.empty()
status_placeholder = st.empty()
result_placeholder = st.empty()

with progress_placeholder.container():
    st.markdown("### Running search...")
    progress = st.progress(0, text="Initializing...")


async def _run_graph(constraints: SearchConstraints):
    from gradscout.graph import graph

    initial_state = {
        "constraints": constraints,
        "messages": [],
        "discovered_programs": [],
        "researched_programs": [],
        "ranked_programs": [],
        "research_index": 0,
        "errors": [],
        "final_table": "",
    }

    steps = []
    async for step in graph.astream(initial_state):
        steps.append(step)
        node = list(step.keys())[0]

        if node == "intake":
            progress.progress(10, text="Constraints loaded...")
        elif node == "discover":
            n = len(list(step.values())[0].get("discovered_programs", []))
            progress.progress(30, text=f"Found {n} programs on mastersportal...")
        elif node == "research":
            idx = list(step.values())[0].get("research_index", 0)
            total = len(initial_state.get("discovered_programs", [])) or max_programs
            pct = 30 + int(60 * idx / max(total, 1))
            progress.progress(min(pct, 89), text=f"Researching program {idx}/{total}...")
        elif node == "rank":
            progress.progress(92, text="Ranking programs...")
        elif node == "output":
            progress.progress(100, text="Done!")

    # Merge all step states to get the final state
    final = {}
    for step in steps:
        for v in step.values():
            final.update(v)
    return final


try:
    final_state = asyncio.run(_run_graph(constraints))
except Exception as exc:
    progress_placeholder.empty()
    st.error(f"Search failed: {exc}")
    st.stop()

progress_placeholder.empty()

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
ranked = final_state.get("ranked_programs", [])
errors = final_state.get("errors", [])

if not ranked:
    st.warning("No programs found. Try broadening your search constraints.")
    if errors:
        with st.expander("Errors"):
            for e in errors:
                st.text(e)
    st.stop()

st.success(f"Found {len(ranked)} matching programs")

# Summary metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Programs found", len(ranked))
m2.metric("Top score", f"{ranked[0].relevance_score}/100")
free_count = sum(1 for r in ranked if r.program.fees_eur_per_year == 0 or "free" in (r.program.fees_display or "").lower())
m3.metric("Free programs", free_count)
with_deadline = sum(1 for r in ranked if r.program.deadline)
m4.metric("With deadline info", with_deadline)

st.divider()

# Results table
st.markdown("### Ranked Programs")

import pandas as pd

rows = []
for i, r in enumerate(ranked, 1):
    p = r.program
    fees = p.fees_display or (f"€{p.fees_eur_per_year:,}/yr" if p.fees_eur_per_year else "Free / N/A")
    rows.append({
        "Rank": i,
        "Program": p.name,
        "University": p.university,
        "Country": p.country,
        "Fees": fees,
        "Deadline": p.deadline or "—",
        "Language": p.language or "—",
        "Score": r.relevance_score,
        "Apply": p.application_url or p.source_url,
    })

df = pd.DataFrame(rows)
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
        "Apply": st.column_config.LinkColumn("Apply", display_text="Open"),
    },
)

# Detailed cards
st.divider()
st.markdown("### Program Details")

for r in ranked:
    p = r.program
    with st.expander(f"**{p.name}** — {p.university}, {p.country} · {r.relevance_score}/100"):
        detail_cols = st.columns(2)
        with detail_cols[0]:
            st.markdown(f"**Fees:** {p.fees_display or 'N/A'}")
            st.markdown(f"**Language:** {p.language or 'N/A'}")
            st.markdown(f"**Duration:** {f'{p.duration_months} months' if p.duration_months else 'N/A'}")
            st.markdown(f"**Deadline:** {p.deadline or 'N/A'}")
            if p.deadline_note:
                st.caption(p.deadline_note)
        with detail_cols[1]:
            if r.reasons:
                st.markdown("**Why it matches:**")
                for reason in r.reasons:
                    st.markdown(f"- {reason}")
            if r.warnings:
                st.markdown("**Check manually:**")
                for warning in r.warnings:
                    st.markdown(f"- {warning}")

        if p.requirements:
            st.markdown("**Requirements:**")
            for req in p.requirements:
                st.markdown(f"- {req}")

        if p.notes:
            st.caption(f"Notes: {p.notes}")

        if p.application_url:
            st.link_button("Go to application page", p.application_url)
        elif p.source_url:
            st.link_button("View program page", p.source_url)

# Errors
if errors:
    with st.expander(f"{len(errors)} programs could not be researched"):
        for e in errors:
            st.text(e)

# Export
st.divider()
st.markdown("### Export")
export_cols = st.columns(2)
with export_cols[0]:
    st.download_button(
        "Download as Markdown",
        data=final_state.get("final_table", ""),
        file_name="grad_scout_results.md",
        mime="text/markdown",
        icon=":material/download:",
    )
with export_cols[1]:
    import json
    export_data = [
        {
            "rank": i,
            "program": r.program.model_dump(),
            "score": r.relevance_score,
            "reasons": r.reasons,
            "warnings": r.warnings,
        }
        for i, r in enumerate(ranked, 1)
    ]
    st.download_button(
        "Download as JSON",
        data=json.dumps(export_data, indent=2),
        file_name="grad_scout_results.json",
        mime="application/json",
        icon=":material/download:",
    )
