"""
HELIOS OS + SEVRA AI
Settings and Configuration Management

Environment-based configuration with strong typing and Pydantic v2 validation.
Supports: development, testing, production environments.
Secrets are NEVER stored in this file — only referenced from Vault/env vars.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base config directory
CONFIG_DIR = Path(__file__).parent


class Settings(BaseSettings):
    """
    Central settings class. All config is type-validated at startup.
    Environment variables override YAML values.
    Prefix: HELIOS_ (e.g., HELIOS_REDIS_HOST)
    """

    model_config = SettingsConfigDict(
        env_prefix="HELIOS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    ENVIRONMENT: Literal["development", "testing", "production"] = Field(
        default="development",
        description="Runtime environment",
    )
    SERVICE_NAME: str = Field(default="helios-backend")
    SERVICE_VERSION: str = Field(default="1.0.0")
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    WORKERS: int = Field(default=4)
    DEBUG: bool = Field(default=False)

    # ── API ───────────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = Field(default="/api/v1")
    API_V2_PREFIX: str = Field(default="/api/v2")
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000"])

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: str | None = Field(default=None)
    REDIS_DB: int = Field(default=0)
    REDIS_SSL: bool = Field(default=False)
    REDIS_MAX_CONNECTIONS: int = Field(default=20)
    REDIS_SOCKET_TIMEOUT: float = Field(default=5.0)
    REDIS_SOCKET_CONNECT_TIMEOUT: float = Field(default=5.0)

    # ── SQLite (Edge / Offline-First) ─────────────────────────────────────────
    SQLITE_PATH: str = Field(default="./data/helios_edge.db")
    SQLITE_ENCRYPTION_KEY: str | None = Field(
        default=None,
        description="SQLCipher AES-256 key. Required in production.",
    )
    SQLITE_POOL_SIZE: int = Field(default=5)
    SQLITE_MAX_OVERFLOW: int = Field(default=10)

    # ── PostgreSQL (Central) ──────────────────────────────────────────────────
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_DB: str = Field(default="helios")
    POSTGRES_USER: str = Field(default="helios")
    POSTGRES_PASSWORD: str | None = Field(default=None)
    POSTGRES_SSL: bool = Field(default=False)
    POSTGRES_POOL_SIZE: int = Field(default=10)
    POSTGRES_MAX_OVERFLOW: int = Field(default=20)
    POSTGRES_POOL_TIMEOUT: float = Field(default=30.0)
    POSTGRES_POOL_RECYCLE: int = Field(default=3600)

    # ── JWT Security ──────────────────────────────────────────────────────────
    JWT_PRIVATE_KEY_PATH: str | None = Field(
        default=None,
        description="Path to RS256 4096-bit RSA private key PEM file",
    )
    JWT_PUBLIC_KEY_PATH: str | None = Field(
        default=None,
        description="Path to RS256 RSA public key PEM file",
    )
    JWT_ALGORITHM: str = Field(default="RS256")
    JWT_ACCESS_TOKEN_EXPIRE_SECONDS: int = Field(default=900)   # 15 minutes
    JWT_REFRESH_TOKEN_EXPIRE_SECONDS: int = Field(default=604800)  # 7 days
    JWT_ISSUER: str = Field(default="helios-security-service")
    JWT_AUDIENCE: str = Field(default="helios-platform")

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: Literal["json", "console"] = Field(default="json")
    LOG_INCLUDE_CALLER: bool = Field(default=False)

    # ── Monitoring ────────────────────────────────────────────────────────────
    METRICS_ENABLED: bool = Field(default=True)
    HEALTH_CHECK_TIMEOUT: float = Field(default=5.0)

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=60)

    # ── Facility ──────────────────────────────────────────────────────────────
    FACILITY_ID: str = Field(default="FACILITY-001")

    # ── Computed Properties ───────────────────────────────────────────────────
    @property
    def postgres_dsn(self) -> str:
        password = self.POSTGRES_PASSWORD or ""
        ssl = "?ssl=require" if self.POSTGRES_SSL else ""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}{ssl}"
        )

    @property
    def sqlite_dsn(self) -> str:
        return f"sqlite+aiosqlite:///{self.SQLITE_PATH}"

    @property
    def redis_url(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        scheme = "rediss" if self.REDIS_SSL else "redis"
        return f"{scheme}://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return upper

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            missing = []
            if not self.JWT_PRIVATE_KEY_PATH:
                missing.append("HELIOS_JWT_PRIVATE_KEY_PATH")
            if not self.JWT_PUBLIC_KEY_PATH:
                missing.append("HELIOS_JWT_PUBLIC_KEY_PATH")
            if not self.POSTGRES_PASSWORD:
                missing.append("HELIOS_POSTGRES_PASSWORD")
            if not self.SQLITE_ENCRYPTION_KEY:
                missing.append("HELIOS_SQLITE_ENCRYPTION_KEY")
            if missing:
                raise ValueError(
                    f"Production requires these secrets to be set: {', '.join(missing)}"
                )
        return self


def _load_yaml_config(environment: str) -> dict[str, Any]:
    """Load YAML configuration for the given environment."""
    files = [
        CONFIG_DIR / "base.yaml",
        CONFIG_DIR / f"{environment}.yaml",
    ]
    merged: dict[str, Any] = {}
    for path in files:
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
                merged.update(data)
    return merged


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns the singleton Settings instance.
    Cached after first call for performance.
    Reads environment from HELIOS_ENVIRONMENT env var (default: development).
    """
    environment = os.getenv("HELIOS_ENVIRONMENT", "development").lower()
    yaml_config = _load_yaml_config(environment)

    # Convert YAML keys to HELIOS_ prefixed env var format for pydantic
    env_overrides: dict[str, Any] = {}
    for key, value in yaml_config.items():
        env_key = f"HELIOS_{key.upper()}"
        # Environment variables take precedence over yaml configs
        if env_key not in os.environ:
            env_overrides[key.upper()] = value

    return Settings(**env_overrides)
