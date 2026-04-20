"""mastersportal.eu discovery scraper."""

from __future__ import annotations

from gradscout.models import DiscoveredProgram, SearchConstraints
from gradscout.utils.logging import get_logger

logger = get_logger(__name__)


async def search_mastersportal(constraints: SearchConstraints) -> list[DiscoveredProgram]:
    """
    Navigate mastersportal.eu with the given constraints and return
    a list of DiscoveredProgram objects from the search results.

    Implemented in Day 2.
    """
    raise NotImplementedError("mastersportal scraper implemented in Day 2")
