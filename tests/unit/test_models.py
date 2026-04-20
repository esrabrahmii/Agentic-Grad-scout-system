"""Unit tests for core Pydantic models."""

from __future__ import annotations

import pytest
from gradscout.models import (
    DiscoveredProgram,
    ProgramInfo,
    RankedProgram,
    SearchConstraints,
)


def test_search_constraints_defaults():
    c = SearchConstraints(fields=["machine learning"])
    assert c.level == "masters"
    assert c.start_year == 2026
    assert c.languages == ["English"]
    assert c.countries == []
    assert c.max_fees_eur_per_year is None


def test_search_constraints_custom():
    c = SearchConstraints(
        fields=["AI", "NLP"],
        countries=["Germany", "Netherlands"],
        max_fees_eur_per_year=3000,
        level="phd",
        start_year=2025,
    )
    assert len(c.fields) == 2
    assert c.max_fees_eur_per_year == 3000
    assert c.level == "phd"


def test_program_info_optional_fields():
    p = ProgramInfo(
        name="MSc AI",
        university="TU Berlin",
        country="Germany",
    )
    assert p.fees_eur_per_year is None
    assert p.deadline is None
    assert p.requirements == []
    assert p.extraction_confidence == "medium"


def test_ranked_program():
    p = ProgramInfo(name="MSc Data Science", university="TU Delft", country="Netherlands")
    r = RankedProgram(program=p, relevance_score=85, reasons=["Free tuition", "English program"])
    assert r.relevance_score == 85
    assert len(r.reasons) == 2
    assert r.warnings == []


def test_discovered_program():
    d = DiscoveredProgram(
        name="MSc Computer Science",
        university="LMU Munich",
        country="Germany",
        mastersportal_url="https://www.mastersportal.eu/studies/123",
    )
    assert d.city == ""
    assert d.program_url == ""
