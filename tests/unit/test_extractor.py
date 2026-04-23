"""Unit tests for the extractor helpers (no LLM calls)."""

from __future__ import annotations

from gradscout.tools.extractor import _truncate_text


def test_truncate_short_text():
    text = "short text"
    assert _truncate_text(text, max_chars=100) == text


def test_truncate_long_text_centers_on_keywords():
    # Build a long text with "requirements" buried in the middle
    prefix = "x" * 3000
    middle = "requirements: BSc in Computer Science, IELTS 6.5"
    suffix = "y" * 3000
    text = prefix + middle + suffix

    result = _truncate_text(text, max_chars=500)
    assert "requirements" in result.lower()
    assert len(result) <= 500


def test_truncate_no_keywords_takes_from_start():
    text = "a" * 10_000
    result = _truncate_text(text, max_chars=500)
    assert len(result) == 500
