"""LLM-powered structured extraction from university program pages."""

from __future__ import annotations

import re

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from gradscout.config import get_settings
from gradscout.models import DiscoveredProgram, ProgramInfo
from gradscout.utils.logging import get_logger

logger = get_logger(__name__)

# Max characters of page text to send to the LLM (keep tokens low)
_MAX_TEXT_CHARS = 6_000

_SYSTEM_PROMPT = """\
You are an academic program information extractor.
Extract structured information from the university webpage text provided.
Only include information that is explicitly stated on the page.
If a field is not mentioned, leave it as null or empty.
Be precise: copy exact deadline dates, exact fee amounts, exact requirement phrases.
"""

_HUMAN_PROMPT = """\
Extract program information from this university webpage.

Program name hint: {program_name}
University hint: {university}
Source URL: {url}

--- PAGE TEXT ---
{page_text}
--- END ---

Extract all available fields. For requirements, list each requirement as a separate string.
"""


class _ExtractedProgram(BaseModel):
    """Intermediate extraction schema — maps to ProgramInfo."""

    name: str = Field(default="", description="Full official program name")
    fees_eur_per_year: int | None = Field(default=None, description="Annual tuition in EUR, null if free or unknown")
    fees_display: str = Field(default="", description="Fees as written on the page, e.g. 'Free for EU students'")
    language: str = Field(default="", description="Primary language of instruction")
    duration_months: int | None = Field(default=None, description="Program duration in months")
    deadline: str | None = Field(default=None, description="Application deadline, e.g. '1 April 2026'")
    deadline_note: str = Field(default="", description="Any notes about the deadline")
    requirements: list[str] = Field(
        default_factory=list,
        description="List of admission requirements, e.g. ['BSc in CS or related field', 'IELTS 6.5']",
    )
    application_url: str = Field(default="", description="Direct link to the application portal")
    notes: str = Field(default="", description="Any other important information")
    extraction_confidence: str = Field(
        default="medium",
        description="How confident you are in the extraction: high, medium, or low",
    )


def _truncate_text(text: str, max_chars: int = _MAX_TEXT_CHARS) -> str:
    """Keep the most relevant portion of the page text."""
    if len(text) <= max_chars:
        return text

    # Try to keep content around keywords likely to contain program info
    keywords = ["requirement", "admission", "tuition", "fee", "deadline", "apply", "duration", "language"]
    text_lower = text.lower()

    best_pos = 0
    for kw in keywords:
        pos = text_lower.find(kw)
        if pos != -1:
            best_pos = max(best_pos, pos)

    # Center the window around the most relevant section
    start = max(0, best_pos - max_chars // 3)
    return text[start: start + max_chars]


async def extract_program_info(
    page_text: str,
    url: str,
    discovered: DiscoveredProgram,
) -> ProgramInfo:
    """
    Send cleaned page text to the extraction LLM and return a ProgramInfo.
    Uses the fast small model (llama-3.1-8b-instant) to stay within rate limits.
    """
    settings = get_settings()
    llm = settings.get_extraction_llm()

    # Structured output — LLM fills in the _ExtractedProgram schema
    structured_llm = llm.with_structured_output(_ExtractedProgram)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("human", _HUMAN_PROMPT),
    ])

    chain = prompt | structured_llm

    truncated = _truncate_text(page_text)

    try:
        result: _ExtractedProgram = await chain.ainvoke({
            "program_name": discovered.name,
            "university": discovered.university,
            "page_text": truncated,
            "url": url,
        })
    except Exception as exc:
        logger.warning("LLM extraction failed, returning partial info", url=url, error=str(exc))
        return ProgramInfo(
            name=discovered.name,
            university=discovered.university,
            country=discovered.country,
            city=discovered.city,
            fees_display=discovered.fees_display,
            language=discovered.language,
            source_url=url,
            extraction_confidence="low",
            notes=f"Extraction failed: {exc}",
        )

    return ProgramInfo(
        name=result.name or discovered.name,
        university=discovered.university,
        country=discovered.country,
        city=discovered.city,
        fees_eur_per_year=result.fees_eur_per_year,
        fees_display=result.fees_display or discovered.fees_display,
        language=result.language or discovered.language,
        duration_months=result.duration_months,
        deadline=result.deadline,
        deadline_note=result.deadline_note,
        requirements=result.requirements,
        application_url=result.application_url,
        source_url=url,
        extraction_confidence=result.extraction_confidence,  # type: ignore[arg-type]
        notes=result.notes,
    )
