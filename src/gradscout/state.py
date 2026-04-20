"""LangGraph agent state definition."""

from __future__ import annotations

from typing import Annotated

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from gradscout.models import (
    DiscoveredProgram,
    ProgramInfo,
    RankedProgram,
    SearchConstraints,
)


class AgentState(TypedDict):
    """State that flows through all LangGraph nodes."""

    # Set once by intake node
    constraints: SearchConstraints

    # Populated by discover node
    discovered_programs: list[DiscoveredProgram]

    # Populated by research node (one per discovered program)
    researched_programs: list[ProgramInfo]

    # Index tracking which program the research loop is currently on
    research_index: int

    # Populated by rank node
    ranked_programs: list[RankedProgram]

    # Final markdown output
    final_table: str

    # Errors collected during execution (non-fatal)
    errors: list[str]

    # LangChain message history (for conversational intake)
    messages: Annotated[list, add_messages]
