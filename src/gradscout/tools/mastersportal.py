"""mastersportal.eu discovery scraper."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup
from langchain_core.prompts import ChatPromptTemplate
from playwright.async_api import Page, async_playwright
from pydantic import BaseModel, Field

from gradscout.config import get_settings
from gradscout.models import DiscoveredProgram, SearchConstraints
from gradscout.utils.logging import get_logger

logger = get_logger(__name__)

_BASE = "https://www.mastersportal.com"
_DEBUG_HTML_PATH = Path("data/debug_mastersportal.html")


def _build_search_url(constraints: SearchConstraints) -> str:
    """Build a mastersportal.eu search URL from constraints."""
    keywords = "+".join(quote_plus(f) for f in constraints.fields)
    params = [f"q={keywords}"]

    if constraints.level == "masters":
        params.append("degree=master")
    elif constraints.level == "phd":
        params.append("degree=phd")

    if constraints.max_fees_eur_per_year == 0:
        params.append("tuition=0,0")
    elif constraints.max_fees_eur_per_year is not None:
        params.append(f"tuition=0,{constraints.max_fees_eur_per_year}")

    if "English" in constraints.languages:
        params.append("language=english")

    params.append(f"limit={constraints.max_programs}")
    params.append(f"start={constraints.start_year}-01-01,{constraints.start_year}-12-31")

    # mastersportal uses /search/{level}# path format
    level_path = "master" if constraints.level == "masters" else constraints.level if constraints.level != "both" else "all"
    return f"{_BASE}/search/{level_path}#{'&'.join(params)}"


def _parse_listing_cards(html: str) -> list[dict]:
    """Parse mastersportal.com search result cards using their actual CSS classes."""
    soup = BeautifulSoup(html, "lxml")

    # Actual class used by mastersportal.com (confirmed from live HTML)
    cards = soup.select(".SearchStudyCard")

    programs = []
    for card in cards:
        try:
            name_el = card.select_one(".StudyName")
            uni_el = card.select_one(".OrganisationName")
            location_el = card.select_one(".OrganisationLocation")
            tuition_el = card.select_one(".TuitionValue")
            duration_el = card.select_one(".DurationValue")
            link_el = card.select_one("a[href*='/studies/']")

            name = name_el.get_text(strip=True) if name_el else ""
            university = uni_el.get_text(strip=True) if uni_el else ""
            location = location_el.get_text(strip=True) if location_el else ""
            tuition = tuition_el.get_text(strip=True) if tuition_el else ""
            duration = duration_el.get_text(strip=True) if duration_el else ""
            href = link_el.get("href", "") if link_el else ""
            mp_url = href if href.startswith("http") else urljoin(_BASE, href)

            # location is typically "City, Country"
            country = location.split(",")[-1].strip() if "," in location else location

            if name and university:
                programs.append({
                    "name": name,
                    "university": university,
                    "country": country,
                    "fees_display": tuition,
                    "duration_display": duration,
                    "language": "",
                    "mastersportal_url": mp_url,
                })
        except Exception:
            continue

    return programs


class _DiscoveredList(BaseModel):
    programs: list[dict] = Field(
        description="List of programs. Each item must have: name, university, country, mastersportal_url"
    )


async def _llm_extract_programs(page_text: str, max_programs: int) -> list[dict]:
    """Fallback: use LLM to extract program listings from raw page text."""
    settings = get_settings()
    llm = settings.get_extraction_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are extracting a list of graduate programs from a university aggregator website. "
            "Return a JSON list of programs. Each program must have: "
            "name (string), university (string), country (string), mastersportal_url (string or empty). "
            f"Return at most {max_programs} programs."
        )),
        ("human", (
            "Extract all graduate programs listed on this page.\n\n"
            "--- PAGE TEXT ---\n{page_text}\n--- END ---\n\n"
            "Return a JSON object with a 'programs' array."
        )),
    ])

    structured_llm = llm.with_structured_output(_DiscoveredList)
    chain = prompt | structured_llm

    # Trim to avoid token limits
    trimmed = page_text[:8000]

    try:
        result: _DiscoveredList = await chain.ainvoke({"page_text": trimmed})
        return result.programs or []
    except Exception as exc:
        logger.warning("LLM program list extraction failed", error=str(exc))
        return []


def _clean_page_text(html: str) -> str:
    """Strip boilerplate and return visible text."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # Collapse excessive blank lines
    import re
    return re.sub(r"\n{3,}", "\n\n", text).strip()


async def _get_program_url(page: Page, mp_url: str, delay: float = 1.0) -> str:
    """Visit a mastersportal program page and extract the university's own URL."""
    try:
        await page.goto(mp_url, timeout=20_000, wait_until="domcontentloaded")
        await asyncio.sleep(delay)

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        link = (
            soup.select_one("a[data-testid='programme-website-link']")
            or soup.select_one("a[rel='nofollow noopener']:not([href*='mastersportal'])")
            or soup.select_one("a.Button--primary[href^='http']:not([href*='mastersportal'])")
        )
        if link:
            return link.get("href", "")
    except Exception as exc:
        logger.warning("Could not get program URL", mp_url=mp_url, error=str(exc))
    return ""


async def search_mastersportal(constraints: SearchConstraints) -> list[DiscoveredProgram]:
    """Search mastersportal.eu and return a list of DiscoveredProgram objects."""
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
            # Use domcontentloaded — networkidle times out on SPAs that keep polling
            await page.goto(search_url, timeout=settings.browser_timeout_ms, wait_until="domcontentloaded")
            # Wait for JS to render search results (React needs time after DOM loads)
            await page.wait_for_load_state("load")
            await asyncio.sleep(5)

            # Dismiss cookie consent if present
            try:
                await page.click("button:has-text('Accept'), button:has-text('Agree'), #onetrust-accept-btn-handler", timeout=3000)
                await asyncio.sleep(1)
            except Exception:
                pass

            html = await page.content()

            # Save debug HTML so we can inspect if parsing fails
            _DEBUG_HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
            _DEBUG_HTML_PATH.write_text(html, encoding="utf-8")
            logger.info("Debug HTML saved", path=str(_DEBUG_HTML_PATH), size=len(html))

            # Strategy 1: CSS selectors
            raw_programs = _parse_listing_cards(html)
            logger.info("CSS selector parse result", count=len(raw_programs))

            # Strategy 2: LLM fallback if selectors found nothing
            if not raw_programs:
                logger.info("CSS selectors returned 0 — falling back to LLM extraction")
                page_text = _clean_page_text(html)
                raw_programs = await _llm_extract_programs(page_text, constraints.max_programs)
                logger.info("LLM extraction result", count=len(raw_programs))

            logger.info("Found programs in listing", count=len(raw_programs))

            # Get university URLs for each program
            programs: list[DiscoveredProgram] = []
            for raw in raw_programs[: constraints.max_programs]:
                name = raw.get("name", "")
                university = raw.get("university", "")
                if not name or not university:
                    continue

                mp_url = raw.get("mastersportal_url", "")
                program_url = ""
                if mp_url:
                    program_url = await _get_program_url(
                        page, mp_url, delay=settings.request_delay_seconds
                    )
                    await asyncio.sleep(settings.request_delay_seconds)

                programs.append(DiscoveredProgram(
                    name=name,
                    university=university,
                    country=raw.get("country", ""),
                    fees_display=raw.get("fees_display", ""),
                    duration_display=raw.get("duration_display", ""),
                    language=raw.get("language", ""),
                    mastersportal_url=mp_url,
                    program_url=program_url,
                ))

            logger.info("Discovery complete", total=len(programs))
            return programs

        finally:
            await browser.close()
