"""Intake node — collects search constraints from the user."""

from __future__ import annotations

from gradscout.models import SearchConstraints
from gradscout.state import AgentState
from gradscout.utils.logging import get_logger

logger = get_logger(__name__)


def intake_node(state: AgentState) -> dict:
    """
    Expects state['constraints'] to already be populated before the graph runs.
    The Streamlit UI or CLI sets constraints directly; this node just validates
    and logs them.
    """
    constraints: SearchConstraints = state["constraints"]

    logger.info(
        "Search constraints received",
        fields=constraints.fields,
        countries=constraints.countries,
        level=constraints.level,
        max_fees=constraints.max_fees_eur_per_year,
        languages=constraints.languages,
        start_year=constraints.start_year,
    )

    return {
        "discovered_programs": [],
        "researched_programs": [],
        "ranked_programs": [],
        "research_index": 0,
        "errors": [],
        "final_table": "",
    }
