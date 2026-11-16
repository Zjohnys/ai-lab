from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> repository root is three levels up.
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application settings, read from environment variables and the root .env file."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    chat_model: str = "qwen3:8b"
    code_model: str = "qwen2.5-coder:7b"
    embedding_model: str = "bge-m3"
    num_ctx: int = 8192
    temperature: float = 0.2
    request_timeout_seconds: float = 120.0
    database_path: str = "./data/ailab.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
