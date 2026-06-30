"""Application settings, loaded from the environment / .env.

The OpenAI-compatible provider settings (LLM_*) match `.env.example`. The
walking skeleton (Issue #2) never calls a real model, but the settings are read
here so the provider can be swapped via `.env` with no code change (story #24).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Where the SQLite file lives. Relative to the backend working directory.
    database_url: str = "sqlite:///./hr_assistant.db"

    # CORS origin for the Next.js dev server.
    frontend_origin: str = "http://localhost:3000"

    # OpenAI-compatible provider settings (see .env.example).
    llm_api_key: str = "sk-not-set"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    llm_timeout: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
