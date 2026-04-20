"""Core Pydantic models for grad-scout."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SearchConstraints(BaseModel):
    """What the user is looking for."""

    fields: list[str] = Field(
        description="Academic fields of interest, e.g. ['machine learning', 'NLP', 'computer science']"
    )
    countries: list[str] = Field(
        default_factory=list,
        description="Target countries, e.g. ['Germany', 'Netherlands']. Empty = all Europe.",
    )
    max_fees_eur_per_year: int | None = Field(
        default=None,
        description="Maximum tuition in EUR/year. None = free programs only.",
    )
    languages: list[str] = Field(
        default_factory=lambda: ["English"],
        description="Accepted languages of instruction.",
    )
    level: Literal["masters", "phd", "both"] = "masters"
    start_year: int = Field(default=2026, description="Target intake year.")
    max_programs: int = Field(
        default=30,
        description="Maximum programs to research in detail.",
    )


class DiscoveredProgram(BaseModel):
    """Minimal info from the discovery phase (mastersportal listing)."""

    name: str
    university: str
    country: str
    city: str = ""
    fees_display: str = ""
    duration_display: str = ""
    language: str = ""
    mastersportal_url: str
    program_url: str = ""


class ProgramInfo(BaseModel):
    """Full structured info extracted from the university's own page."""

    name: str
    university: str
    country: str
    city: str = ""
    fees_eur_per_year: int | None = None
    fees_display: str = ""
    language: str = ""
    duration_months: int | None = None
    deadline: str | None = None
    deadline_note: str = ""
    requirements: list[str] = Field(default_factory=list)
    application_url: str = ""
    source_url: str = ""
    extraction_confidence: Literal["high", "medium", "low"] = "medium"
    notes: str = ""


class RankedProgram(BaseModel):
    """A program with a computed relevance score."""

    program: ProgramInfo
    relevance_score: int = Field(description="0-100, higher = better match to constraints")
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
