from functools import lru_cache
from pathlib import Path

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_ignore_empty=True,
        extra="ignore",
        frozen=True,
        hide_input_in_errors=True,
    )

    langfuse_base_url: HttpUrl = HttpUrl("http://localhost:3000")
    langfuse_public_key: str = Field(min_length=1)
    langfuse_secret_key: SecretStr = Field(min_length=1)
    langfuse_tracing_enabled: bool = True
    langfuse_tracing_environment: str = "development"
    otel_service_name: str | None = None
    specialist_url: HttpUrl = HttpUrl("http://127.0.0.1:8001")
    specialist_timeout_seconds: float = Field(default=10, gt=0)
    google_api_key: SecretStr = SecretStr("")
    adk_model: str = Field(default="gemini-2.5-flash", min_length=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
