from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All secrets stay in the local .env file, never in source code."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-chat"
    supabase_url: str | None = None
    supabase_service_key: str | None = None
    langsmith_tracing: bool = True
    langsmith_api_key: str | None = None
    langsmith_project: str = "my-first-agent"
    frontend_origin: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
