"""后端服务的应用配置。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """从环境变量加载后端配置，并提供合理默认值。"""

    APP_NAME: str = "Agent Platform"
    APP_ENV: str = "local"
    DEBUG: bool = True
    API_PREFIX: str = "/v1"
    CACHE_NAMESPACE: str = "agent-platform"
    GUEST_USER_ID: str = "guest"
    GUEST_USER_NAME: str = "Guest"
    API_KEY_USER_ID_PREFIX: str = "api-key"
    API_KEY_USER_HASH_SALT: str = ""

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agent_platform"
    DATABASE_ECHO: bool = False

    REDIS_ENABLED: bool = False
    REDIS_URL: str = "redis://localhost:6379/0"

    OBJECT_STORAGE_BACKEND: str = "local"
    OBJECT_STORAGE_LOCAL_ROOT: str = "data/object_storage"

    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str | None = None
    LLM_TEMPERATURE: float = 0.2
    LLM_TIMEOUT: int = 60
    LLM_MAX_RETRIES: int = 2

    LANGFUSE_ENABLED: bool = False
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["*"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("API_PREFIX")
    @classmethod
    def normalize_api_prefix(cls, value: str) -> str:
        if not value:
            return "/v1"
        return value if value.startswith("/") else f"/{value}"

    @field_validator(
        "CACHE_NAMESPACE",
        "GUEST_USER_ID",
        "GUEST_USER_NAME",
        "API_KEY_USER_ID_PREFIX",
    )
    @classmethod
    def normalize_non_empty_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("setting value must not be empty")
        return normalized

    @field_validator("OBJECT_STORAGE_BACKEND")
    @classmethod
    def normalize_object_storage_backend(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized in {"", "disabled", "none"}:
            return "disabled"
        if normalized == "local":
            return normalized
        raise ValueError("OBJECT_STORAGE_BACKEND must be one of: local, disabled")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return ["*"]
        if isinstance(value, str):
            if value.strip() == "*":
                return ["*"]
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return value
        return ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
