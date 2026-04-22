"""Playwright browser wrapper — fetch and clean page text."""

from __future__ import annotations

import asyncio
import re

from bs4 import BeautifulSoup

from gradscout.config import get_settings
from gradscout.utils.logging import get_logger

logger = get_logger(__name__)

# Tags whose content we strip entirely before extracting text
_STRIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"}


def _clean_html(html: str) -> str:
    """Strip boilerplate tags and return clean visible text."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(_STRIP_TAGS):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def fetch_page_text(url: str, timeout_ms: int | None = None) -> str:
    """
    Navigate to *url* with a headless Playwright browser and return
    the cleaned visible text content (scripts, nav, footer stripped).
    """
    from playwright.async_api import async_playwright

    settings = get_settings()
    timeout = timeout_ms or settings.browser_timeout_ms

    logger.debug("Fetching page", url=url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.headless)
        try:
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")

            # Wait briefly for JS to render dynamic content
            await asyncio.sleep(1.5)

            html = await page.content()
            text = _clean_html(html)
            logger.debug("Page fetched", url=url, chars=len(text))
            return text
        finally:
            await browser.close()


async def fetch_page_html(url: str, timeout_ms: int | None = None) -> str:
    """Return raw HTML (for cases where structure matters)."""
    from playwright.async_api import async_playwright

    settings = get_settings()
    timeout = timeout_ms or settings.browser_timeout_ms

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.headless)
        try:
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            await asyncio.sleep(1.5)
            return await page.content()
        finally:
            await browser.close()
