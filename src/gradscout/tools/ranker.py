"""Rule-based + LLM scoring of programs against user constraints."""

from __future__ import annotations

from gradscout.models import ProgramInfo, RankedProgram, SearchConstraints
from gradscout.utils.logging import get_logger

logger = get_logger(__name__)


def _fees_score(program: ProgramInfo, constraints: SearchConstraints) -> tuple[int, list[str], list[str]]:
    """Score fees constraint. Returns (points, reasons, warnings)."""
    reasons, warnings = [], []

    if constraints.max_fees_eur_per_year == 0:
        # User wants free only
        if program.fees_eur_per_year is None and "free" in (program.fees_display or "").lower():
            reasons.append("Free tuition")
            return 25, reasons, warnings
        elif program.fees_eur_per_year is None:
            warnings.append("Tuition not found on page — verify manually")
            return 10, reasons, warnings
        elif program.fees_eur_per_year == 0:
            reasons.append("Free tuition confirmed")
            return 25, reasons, warnings
        else:
            warnings.append(f"Tuition is €{program.fees_eur_per_year:,}/yr (you requested free)")
            return 0, reasons, warnings

    if constraints.max_fees_eur_per_year is None:
        # No fee constraint
        return 15, reasons, warnings

    if program.fees_eur_per_year is None:
        warnings.append("Tuition not found — verify manually")
        return 10, reasons, warnings

    if program.fees_eur_per_year <= constraints.max_fees_eur_per_year:
        reasons.append(f"Tuition €{program.fees_eur_per_year:,}/yr within budget")
        return 25, reasons, warnings

    warnings.append(f"Tuition €{program.fees_eur_per_year:,}/yr exceeds budget of €{constraints.max_fees_eur_per_year:,}")
    return 0, reasons, warnings


def _language_score(program: ProgramInfo, constraints: SearchConstraints) -> tuple[int, list[str], list[str]]:
    reasons, warnings = [], []
    if not constraints.languages:
        return 15, reasons, warnings

    prog_lang = (program.language or "").lower()
    for lang in constraints.languages:
        if lang.lower() in prog_lang:
            reasons.append(f"Taught in {lang}")
            return 20, reasons, warnings

    if not prog_lang:
        warnings.append("Language of instruction not found — verify manually")
        return 10, reasons, warnings

    warnings.append(f"Taught in {program.language}, not in your preferred language(s)")
    return 0, reasons, warnings


def _deadline_score(program: ProgramInfo, constraints: SearchConstraints) -> tuple[int, list[str], list[str]]:
    reasons, warnings = [], []
    if program.deadline:
        reasons.append(f"Deadline: {program.deadline}")
        return 15, reasons, warnings
    warnings.append("No deadline found — check university website")
    return 5, reasons, warnings


def _requirements_score(program: ProgramInfo) -> tuple[int, list[str], list[str]]:
    reasons, warnings = [], []
    if program.requirements:
        reasons.append(f"{len(program.requirements)} requirements extracted")
        return 15, reasons, warnings
    warnings.append("Requirements not extracted — check university website")
    return 5, reasons, warnings


def _confidence_score(program: ProgramInfo) -> int:
    return {"high": 10, "medium": 5, "low": 0}.get(program.extraction_confidence, 5)


def score_programs(
    programs: list[ProgramInfo],
    constraints: SearchConstraints,
) -> list[RankedProgram]:
    """
    Score each program 0-100 against the user's constraints.

    Scoring breakdown:
    - Fees match:        0-25 pts
    - Language match:    0-20 pts
    - Deadline present:  5-15 pts
    - Requirements found: 5-15 pts
    - Country match:     0-15 pts
    - Extraction quality: 0-10 pts
    Total: up to 100
    """
    ranked = []

    for program in programs:
        score = 0
        all_reasons: list[str] = []
        all_warnings: list[str] = []

        # Fees
        pts, r, w = _fees_score(program, constraints)
        score += pts
        all_reasons.extend(r)
        all_warnings.extend(w)

        # Language
        pts, r, w = _language_score(program, constraints)
        score += pts
        all_reasons.extend(r)
        all_warnings.extend(w)

        # Deadline
        pts, r, w = _deadline_score(program, constraints)
        score += pts
        all_reasons.extend(r)
        all_warnings.extend(w)

        # Requirements extracted
        pts, r, w = _requirements_score(program)
        score += pts
        all_reasons.extend(r)
        all_warnings.extend(w)

        # Country match
        if constraints.countries:
            if any(c.lower() in (program.country or "").lower() for c in constraints.countries):
                score += 15
                all_reasons.append(f"Located in {program.country}")
        else:
            score += 10  # no country preference, partial credit

        # Extraction confidence
        score += _confidence_score(program)

        ranked.append(
            RankedProgram(
                program=program,
                relevance_score=min(score, 100),
                reasons=all_reasons,
                warnings=all_warnings,
            )
        )

    return ranked
