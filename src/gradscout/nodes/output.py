"""Output node — formats the ranked programs into a markdown table."""

from __future__ import annotations

from gradscout.state import AgentState
from gradscout.utils.logging import get_logger

logger = get_logger(__name__)

_HEADER = (
    "| # | Program | University | Country | Fees | Deadline | Language | Score | Apply |\n"
    "|---|---------|------------|---------|------|----------|----------|-------|-------|\n"
)


def output_node(state: AgentState) -> dict:
    """Builds the final markdown comparison table."""
    ranked = state.get("ranked_programs", [])
    errors = state.get("errors", [])

    if not ranked:
        table = "_No programs matched your constraints._\n"
        if errors:
            table += "\n**Errors during research:**\n" + "\n".join(f"- {e}" for e in errors)
        return {"final_table": table}

    rows = []
    for i, r in enumerate(ranked, 1):
        p = r.program
        fees = p.fees_display or (f"€{p.fees_eur_per_year:,}/yr" if p.fees_eur_per_year else "Free / N/A")
        deadline = p.deadline or "—"
        apply_link = f"[Apply]({p.application_url})" if p.application_url else "—"
        rows.append(
            f"| {i} | {p.name} | {p.university} | {p.country} "
            f"| {fees} | {deadline} | {p.language or '—'} "
            f"| {r.relevance_score}/100 | {apply_link} |"
        )

    table = _HEADER + "\n".join(rows)

    if errors:
        table += f"\n\n> {len(errors)} program(s) could not be researched due to errors."

    logger.info("Output ready", programs=len(ranked), errors=len(errors))
    return {"final_table": table}
