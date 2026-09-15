from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"

    route_db_path: Path = Path("data/routeguard.db")
    groq_api_key: SecretStr | None = None
    groq_model: str = "qwen/qwen3-32b"
    groq_judge_model: str = "openai/gpt-oss-20b"
    groq_max_tokens: int = 400
    groq_judge_max_tokens: int = 500

    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr | None = None
    langsmith_project: str = "routeguard"


@lru_cache
def get_settings() -> Settings:
    return Settings()
