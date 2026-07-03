"""Quorum — Application Configuration"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./quorum.db"

    # ── JWT ───────────────────────────────────────────────────
    SECRET_KEY: str = "quorum-super-secret-change-in-production-use-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── LLM ───────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o"

    # ── GitHub ────────────────────────────────────────────────
    GITHUB_TOKEN: str = ""

    # ── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000"

    # ── App ───────────────────────────────────────────────────
    APP_NAME: str = "Quorum"
    APP_ENV: str = "development"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
