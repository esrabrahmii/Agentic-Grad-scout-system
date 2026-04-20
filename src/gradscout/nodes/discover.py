"""Discover node — searches mastersportal.eu and returns a list of programs."""

from __future__ import annotations

from gradscout.state import AgentState
from gradscout.utils.logging import get_logger

logger = get_logger(__name__)


async def discover_node(state: AgentState) -> dict:
    """
    Uses Playwright to query mastersportal.eu with the user's constraints
    and returns a list of DiscoveredProgram objects.

    Implemented in Day 2.
    """
    from gradscout.tools.mastersportal import search_mastersportal

    constraints = state["constraints"]
    logger.info("Starting discovery", fields=constraints.fields, countries=constraints.countries)

    programs = await search_mastersportal(constraints)

    logger.info("Discovery complete", count=len(programs))
    return {"discovered_programs": programs}
