"""Playwright browser wrapper — fetch and clean page text."""

from __future__ import annotations

import asyncio

from gradscout.utils.logging import get_logger

logger = get_logger(__name__)


async def fetch_page_text(url: str, timeout_ms: int = 30_000) -> str:
    """
    Navigate to *url* with a headless Playwright browser and return
    the visible text content (scripts, styles, nav stripped).

    Implemented in Day 2.
    """
    raise NotImplementedError("Browser tool implemented in Day 2")
