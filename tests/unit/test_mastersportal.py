"""Unit tests for mastersportal URL builder and HTML parser."""

from __future__ import annotations

from gradscout.models import SearchConstraints
from gradscout.tools.mastersportal import _build_search_url, _parse_listing_cards


def test_build_url_free_only():
    c = SearchConstraints(fields=["machine learning"], max_fees_eur_per_year=0)
    url = _build_search_url(c)
    assert "machine" in url
    assert "tuition=0,0" in url
    assert "degree=master" in url


def test_build_url_with_countries_and_fees():
    c = SearchConstraints(
        fields=["NLP", "AI"],
        max_fees_eur_per_year=5000,
        level="phd",
        start_year=2026,
    )
    url = _build_search_url(c)
    assert "tuition=0,5000" in url
    assert "degree=phd" in url
    assert "2026" in url


def test_build_url_both_levels():
    c = SearchConstraints(fields=["data science"], level="both")
    url = _build_search_url(c)
    assert "degree" not in url


def test_parse_listing_cards_empty_html():
    result = _parse_listing_cards("<html><body></body></html>")
    assert result == []


def test_parse_listing_cards_with_card():
    html = """
    <html><body>
    <article class="ProgramCard" data-program-id="123">
      <h3 class="ProgramCard-title">MSc Artificial Intelligence</h3>
      <span class="ProgramCard-university">TU Berlin</span>
      <span class="ProgramCard-country">Germany</span>
      <span class="ProgramCard-tuition">Free</span>
      <span class="ProgramCard-language">English</span>
      <a class="ProgramCard-link" href="/studies/123/msc-ai-tu-berlin">Details</a>
    </article>
    </body></html>
    """
    result = _parse_listing_cards(html)
    assert len(result) == 1
    assert result[0]["name"] == "MSc Artificial Intelligence"
    assert result[0]["university"] == "TU Berlin"
    assert result[0]["country"] == "Germany"
    assert "mastersportal.eu" in result[0]["mastersportal_url"]
