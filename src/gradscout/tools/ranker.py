"""Rule-based + LLM scoring of programs against user constraints."""

from __future__ import annotations

from gradscout.models import ProgramInfo, RankedProgram, SearchConstraints
from gradscout.utils.logging import get_logger

logger = get_logger(__name__)


def score_programs(
    programs: list[ProgramInfo],
    constraints: SearchConstraints,
) -> list[RankedProgram]:
    """
    Score each program 0-100 against the user's constraints.
    Rule-based for hard constraints (fees, language, deadline).
    LLM-based for field relevance.

    Implemented in Day 5.
    """
    raise NotImplementedError("Ranker implemented in Day 5")
