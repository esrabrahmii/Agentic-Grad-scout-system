"""mastersportal.eu discovery scraper."""

from __future__ import annotations

import asyncio
import re
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup
from playwright.async_api import Page, async_playwright

from gradscout.config import get_settings
from gradscout.models import DiscoveredProgram, SearchConstraints
from gradscout.utils.logging import get_logger

logger = get_logger(__name__)

_BASE = "https://www.mastersportal.eu"


def _build_search_url(constraints: SearchConstraints) -> str:
    """
    Build a mastersportal.eu search URL from constraints.

    Example:
    https://www.mastersportal.eu/search/#q=machine+learning&limit=30&tuition=0,5000&...
    """
    keywords = "+".join(quote_plus(f) for f in constraints.fields)

    params = [f"q={keywords}"]

    # Degree level
    if constraints.level == "masters":
        params.append("degree=master")
    elif constraints.level == "phd":
        params.append("degree=phd")
    # "both" → no filter

    # Tuition filter
    if constraints.max_fees_eur_per_year is not None and constraints.max_fees_eur_per_year == 0:
        params.append("tuition=0,0")  # free only
    elif constraints.max_fees_eur_per_year is not None:
        params.append(f"tuition=0,{constraints.max_fees_eur_per_year}")

    # Language
    if "English" in constraints.languages:
        params.append("language=english")

    # Limit
    params.append(f"limit={constraints.max_programs}")

    # Start year
    params.append(f"start={constraints.start_year}-01-01,{constraints.start_year}-12-31")

    query = "&".join(params)
    return f"{_BASE}/search/#{query}"


def _parse_listing_cards(html: str) -> list[dict]:
    """Parse program cards from mastersportal search results HTML."""
    soup = BeautifulSoup(html, "lxml")
    programs = []

    # mastersportal uses article.ProgramCard or div[data-program-id] elements
    cards = soup.select("article.ProgramCard, [data-program-id]")

    for card in cards:
        try:
            name_el = card.select_one(".ProgramCard-title, .programme-name, h3, h2")
            uni_el = card.select_one(".ProgramCard-university, .university-name, .institution")
            country_el = card.select_one(".ProgramCard-country, .country, [data-country]")
            fees_el = card.select_one(".ProgramCard-tuition, .tuition, .fees")
            duration_el = card.select_one(".ProgramCard-duration, .duration")
            lang_el = card.select_one(".ProgramCard-language, .language")
            link_el = card.select_one("a[href*='/studies/'], a.ProgramCard-link")

            name = name_el.get_text(strip=True) if name_el else ""
            university = uni_el.get_text(strip=True) if uni_el else ""
            country = country_el.get_text(strip=True) if country_el else ""
            fees = fees_el.get_text(strip=True) if fees_el else ""
            duration = duration_el.get_text(strip=True) if duration_el else ""
            language = lang_el.get_text(strip=True) if lang_el else ""
            href = link_el.get("href", "") if link_el else ""
            mp_url = urljoin(_BASE, href) if href else ""

            if name and university:
                programs.append({
                    "name": name,
                    "university": university,
                    "country": country,
                    "fees_display": fees,
                    "duration_display": duration,
                    "language": language,
                    "mastersportal_url": mp_url,
                })
        except Exception as exc:
            logger.warning("Failed to parse card", error=str(exc))
            continue

    return programs


async def _get_program_url(page: Page, mp_url: str, delay: float = 1.0) -> str:
    """
    Visit a mastersportal program page and extract the link to the
    university's own program page.
    """
    try:
        await page.goto(mp_url, timeout=20_000, wait_until="domcontentloaded")
        await asyncio.sleep(delay)

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        # mastersportal links to the university page via "Visit programme website" button
        link = soup.select_one(
            "a[data-testid='programme-website-link'], "
            "a.Button--primary[href^='http']:not([href*='mastersportal']), "
            "a[rel='nofollow noopener']:not([href*='mastersportal'])"
        )
        if link:
            return link.get("href", "")
    except Exception as exc:
        logger.warning("Could not get program URL", mp_url=mp_url, error=str(exc))
    return ""


async def search_mastersportal(constraints: SearchConstraints) -> list[DiscoveredProgram]:
    """
    Navigate mastersportal.eu with the given constraints and return
    a list of DiscoveredProgram objects from the search results.
    """
    settings = get_settings()
    search_url = _build_search_url(constraints)
    logger.info("Searching mastersportal", url=search_url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        try:
            # Load search results
            await page.goto(search_url, timeout=settings.browser_timeout_ms, wait_until="domcontentloaded")
            # Wait for JS to render the results list
            await asyncio.sleep(3)

            html = await page.content()
            raw_programs = _parse_listing_cards(html)

            if not raw_programs:
                # Fallback: try scrolling to trigger lazy-load
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                html = await page.content()
                raw_programs = _parse_listing_cards(html)

            logger.info("Found programs in listing", count=len(raw_programs))

            # For each program, get the university's own URL
            programs: list[DiscoveredProgram] = []
            for raw in raw_programs[: constraints.max_programs]:
                program_url = ""
                if raw.get("mastersportal_url"):
                    program_url = await _get_program_url(
                        page, raw["mastersportal_url"], delay=settings.request_delay_seconds
                    )
                    await asyncio.sleep(settings.request_delay_seconds)

                programs.append(
                    DiscoveredProgram(
                        name=raw["name"],
                        university=raw["university"],
                        country=raw["country"],
                        fees_display=raw.get("fees_display", ""),
                        duration_display=raw.get("duration_display", ""),
                        language=raw.get("language", ""),
                        mastersportal_url=raw["mastersportal_url"],
                        program_url=program_url,
                    )
                )

            logger.info("Discovery complete", total=len(programs))
            return programs

        finally:
            await browser.close()
