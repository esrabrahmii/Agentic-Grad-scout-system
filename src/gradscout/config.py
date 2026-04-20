"""Application configuration via environment variables."""

from __future__ import annotations

import os
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM providers
    groq_api_key: str = ""
    openai_api_key: str = ""

    # Which provider / models to use
    llm_provider: Literal["groq", "openai"] = "groq"

    # Small fast model for HTML extraction (runs per-program)
    extraction_model: str = "llama-3.1-8b-instant"

    # Larger model for ranking / reasoning (runs once)
    reasoning_model: str = "llama-3.3-70b-versatile"

    # Browser
    headless: bool = True          # set False to watch the browser
    browser_timeout_ms: int = 30_000

    # Scraping
    mastersportal_base_url: str = "https://www.mastersportal.eu"
    max_programs: int = 30         # cap to avoid rate limits
    request_delay_seconds: float = 1.5  # polite delay between page loads

    # Cache
    cache_db_path: str = "data/cache.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_extraction_llm(self):
        """Return a LangChain LLM instance for extraction tasks."""
        if self.llm_provider == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=self.extraction_model,
                api_key=self.groq_api_key,
                temperature=0,
            )
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini", api_key=self.openai_api_key, temperature=0)

    def get_reasoning_llm(self):
        """Return a LangChain LLM instance for reasoning/ranking tasks."""
        if self.llm_provider == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=self.reasoning_model,
                api_key=self.groq_api_key,
                temperature=0,
            )
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o", api_key=self.openai_api_key, temperature=0)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
