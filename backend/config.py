"""Quorum — Application Configuration"""

from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./quorum.db"

    # ── JWT ───────────────────────────────────────────────────
    # Accept either SECRET_KEY or JWT_SECRET from the environment/.env.
    SECRET_KEY: str = Field(
        default="quorum-super-secret-change-in-production-use-long-random-string",
        validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET"),
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── LLM ───────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""          # leave blank if using Groq
    GROQ_API_KEY:   str = ""          # get free key at console.groq.com
    LLM_PROVIDER:   str = "groq"      # "groq" | "openai"
    LLM_MODEL:      str = "llama-3.3-70b-versatile"  # best free Groq model

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
