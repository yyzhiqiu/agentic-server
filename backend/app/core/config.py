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
    AGENT_CHECKPOINT_ENABLED: bool = True
    AGENT_CHECKPOINT_URL: str | None = None
    AGENT_CHECKPOINT_CONNECT_TIMEOUT_SECONDS: int = 3

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

    AMAP_MCP_BASE_URL: str = "https://mcp.amap.com/mcp"
    AMAP_MCP_KEY: str = ""
    AMAP_MCP_TIMEOUT_SECONDS: int = 30

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

    @field_validator("AGENT_CHECKPOINT_URL", "LLM_BASE_URL", "AMAP_MCP_BASE_URL", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return str(value)

    @field_validator("OBJECT_STORAGE_BACKEND")
    @classmethod
    def normalize_object_storage_backend(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized in {"", "disabled", "none"}:
            return "disabled"
        if normalized == "local":
            return normalized
        raise ValueError("OBJECT_STORAGE_BACKEND must be one of: local, disabled")

    @field_validator("AGENT_CHECKPOINT_CONNECT_TIMEOUT_SECONDS", "AMAP_MCP_TIMEOUT_SECONDS")
    @classmethod
    def validate_checkpoint_timeout(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("timeout setting must be greater than 0")
        return value

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
