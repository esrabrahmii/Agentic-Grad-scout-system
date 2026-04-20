"""Research node — visits each program's university page and extracts structured info."""

from __future__ import annotations

from gradscout.state import AgentState
from gradscout.utils.logging import get_logger

logger = get_logger(__name__)


async def research_node(state: AgentState) -> dict:
    """
    Processes one program at a time (research_index tracks position).
    Visits the program's university page and extracts ProgramInfo via LLM.

    Implemented in Day 3.
    """
    from gradscout.tools.extractor import extract_program_info
    from gradscout.tools.browser import fetch_page_text

    idx = state["research_index"]
    discovered = state["discovered_programs"]

    if idx >= len(discovered):
        return {}

    program = discovered[idx]
    logger.info("Researching program", index=idx, name=program.name, university=program.university)

    errors = list(state.get("errors", []))
    researched = list(state.get("researched_programs", []))

    try:
        url = program.program_url or program.mastersportal_url
        page_text = await fetch_page_text(url)
        info = await extract_program_info(page_text, url, program)
        researched.append(info)
    except Exception as exc:
        logger.warning("Failed to research program", name=program.name, error=str(exc))
        errors.append(f"{program.name} @ {program.university}: {exc}")

    return {
        "researched_programs": researched,
        "research_index": idx + 1,
        "errors": errors,
    }


def should_continue_research(state: AgentState) -> str:
    """LangGraph conditional edge: keep looping or move to rank."""
    idx = state.get("research_index", 0)
    total = len(state.get("discovered_programs", []))
    if idx < total:
        return "research"
    return "rank"
