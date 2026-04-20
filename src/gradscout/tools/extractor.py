"""LLM-powered structured extraction from university pages."""

from __future__ import annotations

from gradscout.models import DiscoveredProgram, ProgramInfo
from gradscout.utils.logging import get_logger

logger = get_logger(__name__)


async def extract_program_info(
    page_text: str,
    url: str,
    discovered: DiscoveredProgram,
) -> ProgramInfo:
    """
    Send cleaned page text to the extraction LLM and return a ProgramInfo.

    Implemented in Day 3.
    """
    raise NotImplementedError("Extractor implemented in Day 3")
