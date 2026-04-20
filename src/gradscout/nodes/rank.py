"""Rank node — scores and sorts researched programs against user constraints."""

from __future__ import annotations

from gradscout.models import RankedProgram
from gradscout.state import AgentState
from gradscout.utils.logging import get_logger

logger = get_logger(__name__)


def rank_node(state: AgentState) -> dict:
    """
    Scores each ProgramInfo against the user's SearchConstraints.
    Uses rule-based scoring for hard constraints (fees, language, deadline)
    and LLM reasoning for soft fit (field relevance).

    Implemented in Day 5.
    """
    from gradscout.tools.ranker import score_programs

    constraints = state["constraints"]
    programs = state["researched_programs"]

    logger.info("Ranking programs", count=len(programs))
    ranked = score_programs(programs, constraints)
    ranked.sort(key=lambda r: r.relevance_score, reverse=True)

    logger.info("Ranking complete", top_score=ranked[0].relevance_score if ranked else 0)
    return {"ranked_programs": ranked}
