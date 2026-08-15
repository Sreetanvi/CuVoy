"""Pydantic settings — env names from PROJECT_SPEC §23."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_supabase_url(url: str) -> str:
    """Project origin only. Keep-alive and the REST client append /rest/v1."""
    cleaned = url.strip().strip("\"'").rstrip("/")
    if cleaned.endswith("/rest/v1"):
        cleaned = cleaned[: -len("/rest/v1")]
    return cleaned.rstrip("/")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mapbox_access_token: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    opentripmap_api_key: str = ""
    geonames_username: str = ""
    fastapi_secret_key: str = ""
    cors_origins: str = "http://localhost:3000,https://cuvoy.vercel.app"
    sentry_dsn: str = ""
    log_level: str = "INFO"
    gemini_fast_model: str = "gemini-2.5-flash-lite"
    gemini_balanced_model: str = "gemini-2.5-flash"
    gemini_reasoning_model: str = "gemini-2.5-pro"
    groq_fast_model: str = "llama-3.1-8b-instant"
    groq_balanced_model: str = "llama-3.3-70b-versatile"
    groq_reasoning_model: str = "llama-3.3-70b-versatile"
    openrouter_fast_model: str = "meta-llama/llama-3.3-8b-instruct:free"
    openrouter_balanced_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    openrouter_reasoning_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    @field_validator("*", mode="before")
    @classmethod
    def strip_wrapping_quotes(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().strip("\"'")
        return value

    @field_validator("supabase_url", mode="after")
    @classmethod
    def strip_rest_path(cls, value: str) -> str:
        return normalize_supabase_url(value) if value else value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def cache_configured(self) -> bool:
        return bool(self.upstash_redis_rest_url and self.upstash_redis_rest_token)

    @property
    def db_configured(self) -> bool:
        return bool(self.supabase_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
