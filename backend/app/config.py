"""Application configuration.

Everything is environment-driven with local-friendly fallbacks:
- DATABASE_URL unset  -> SQLite file next to the backend (no Docker needed)
- REDIS_URL unset     -> in-process TTL cache
- ANTHROPIC_API_KEY unset -> deterministic rule-based review provider
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BACKEND_DIR / "knowledge"


class Settings(BaseSettings):
    app_name: str = "AI Resume Reviewer"
    debug: bool = False

    # Database: falls back to a local SQLite file when Postgres isn't configured.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'resume_reviewer.db').as_posix()}"

    # Cache: falls back to an in-process TTL cache when Redis isn't configured.
    redis_url: str | None = None
    cache_ttl_seconds: int = 60 * 60 * 24  # 24h

    # Auth
    jwt_secret: str = "dev-only-change-me-in-production-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24

    # Claude
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"

    # RAG
    rag_top_k: int = 4

    # CORS: comma-separated list of allowed frontend origins.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3010,http://127.0.0.1:3010"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
