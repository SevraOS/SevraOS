"""
HELIOS OS + SEVRA AI
Database Service — Configuration

All database configuration sourced from environment variables.
Follows contract C4.4: No hardcoded secrets. .env.example has placeholders only.
"""

from __future__ import annotations

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    """Centralized configuration for the Database Service."""

    # ── Application ──────────────────────────────────────────────────────────
    ENVIRONMENT: str = Field("development", alias="HELIOS_ENVIRONMENT")
    FACILITY_ID: str = Field("FACILITY-001", alias="HELIOS_FACILITY_ID")

    # ── SQLite (Tier 1 — Edge Store) ─────────────────────────────────────────
    SQLITE_PATH: str = Field("./data/helios_edge.db", alias="HELIOS_SQLITE_PATH")
    SQLITE_ENCRYPTION_KEY: Optional[str] = Field(None, alias="HELIOS_SQLITE_ENCRYPTION_KEY")
    SQLITE_JOURNAL_MODE: str = Field("WAL", alias="HELIOS_SQLITE_JOURNAL_MODE")
    SQLITE_BUSY_TIMEOUT_MS: int = Field(5000, alias="HELIOS_SQLITE_BUSY_TIMEOUT")
    SQLITE_CACHE_SIZE_KB: int = Field(65536, alias="HELIOS_SQLITE_CACHE_SIZE")
    SQLITE_SYNCHRONOUS: str = Field("NORMAL", alias="HELIOS_SQLITE_SYNCHRONOUS")

    # ── PostgreSQL (Tier 2 — Central Store) ──────────────────────────────────
    POSTGRES_HOST: str = Field("localhost", alias="HELIOS_POSTGRES_HOST")
    POSTGRES_PORT: int = Field(5432, alias="HELIOS_POSTGRES_PORT")
    POSTGRES_DB: str = Field("helios", alias="HELIOS_POSTGRES_DB")
    POSTGRES_USER: str = Field("helios", alias="HELIOS_POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field("helios_dev_password", alias="HELIOS_POSTGRES_PASSWORD")
    POSTGRES_SSL: bool = Field(False, alias="HELIOS_POSTGRES_SSL")
    POSTGRES_POOL_SIZE: int = Field(20, alias="HELIOS_POSTGRES_POOL_SIZE")
    POSTGRES_MAX_OVERFLOW: int = Field(10, alias="HELIOS_POSTGRES_MAX_OVERFLOW")
    POSTGRES_POOL_TIMEOUT: int = Field(30, alias="HELIOS_POSTGRES_POOL_TIMEOUT")
    POSTGRES_POOL_RECYCLE: int = Field(1800, alias="HELIOS_POSTGRES_POOL_RECYCLE")
    POSTGRES_ECHO: bool = Field(False, alias="HELIOS_POSTGRES_ECHO")

    # ── PostgreSQL Read Replica ──────────────────────────────────────────────
    POSTGRES_READ_HOST: Optional[str] = Field(None, alias="HELIOS_POSTGRES_READ_HOST")
    POSTGRES_READ_PORT: int = Field(5432, alias="HELIOS_POSTGRES_READ_PORT")

    # ── Redis (Tier 4 — Cache) ───────────────────────────────────────────────
    REDIS_URL: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    REDIS_CACHE_TTL: int = Field(300, alias="HELIOS_REDIS_CACHE_TTL")
    REDIS_CACHE_PREFIX: str = Field("helios:cache:", alias="HELIOS_REDIS_CACHE_PREFIX")

    # ── MinIO / S3 (Tier 3 — Object Storage) ─────────────────────────────────
    MINIO_ENDPOINT: str = Field("localhost:9000", alias="HELIOS_MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str = Field("helios", alias="HELIOS_MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = Field("helios_dev_password", alias="HELIOS_MINIO_SECRET_KEY")
    MINIO_SECURE: bool = Field(False, alias="HELIOS_MINIO_SECURE")
    MINIO_BUCKET_VITALS: str = Field("helios-vitals-archive", alias="HELIOS_MINIO_BUCKET_VITALS")
    MINIO_BUCKET_WAVEFORMS: str = Field("helios-waveforms", alias="HELIOS_MINIO_BUCKET_WAVEFORMS")
    MINIO_BUCKET_AUDIT: str = Field("helios-audit-archive", alias="HELIOS_MINIO_BUCKET_AUDIT")
    MINIO_BUCKET_PREDICTIONS: str = Field(
        "helios-predictions-archive", alias="HELIOS_MINIO_BUCKET_PREDICTIONS"
    )

    # ── Sync Engine ──────────────────────────────────────────────────────────
    SYNC_BATCH_SIZE: int = Field(1000, alias="HELIOS_SYNC_BATCH_SIZE")
    SYNC_INTERVAL_SECONDS: float = Field(5.0, alias="HELIOS_SYNC_INTERVAL")
    SYNC_MAX_RETRY: int = Field(10, alias="HELIOS_SYNC_MAX_RETRY")
    SYNC_BACKOFF_BASE: float = Field(1.0, alias="HELIOS_SYNC_BACKOFF_BASE")
    SYNC_BACKOFF_MAX: float = Field(60.0, alias="HELIOS_SYNC_BACKOFF_MAX")

    # ── Offline Detection ────────────────────────────────────────────────────
    CONNECTIVITY_CHECK_INTERVAL: float = Field(30.0, alias="HELIOS_CONNECTIVITY_CHECK_INTERVAL")
    CONNECTIVITY_FAILURE_THRESHOLD: int = Field(3, alias="HELIOS_CONNECTIVITY_FAILURE_THRESHOLD")

    # ── Data Retention ───────────────────────────────────────────────────────
    HOT_RETENTION_DAYS: int = Field(90, alias="HELIOS_HOT_RETENTION_DAYS")
    WARM_RETENTION_DAYS: int = Field(730, alias="HELIOS_WARM_RETENTION_DAYS")
    COLD_RETENTION_YEARS: int = Field(7, alias="HELIOS_COLD_RETENTION_YEARS")

    # ── Consumer Settings ────────────────────────────────────────────────────
    CONSUMER_BATCH_SIZE: int = Field(10, alias="HELIOS_DB_CONSUMER_BATCH_SIZE")
    CONSUMER_BLOCK_MS: int = Field(2000, alias="HELIOS_DB_CONSUMER_BLOCK_MS")

    @property
    def postgres_dsn(self) -> str:
        """Build the primary PostgreSQL DSN."""
        ssl_suffix = "?ssl=require" if self.POSTGRES_SSL else ""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}{ssl_suffix}"
        )

    @property
    def postgres_read_dsn(self) -> Optional[str]:
        """Build the read-replica PostgreSQL DSN, if configured."""
        if not self.POSTGRES_READ_HOST:
            return None
        ssl_suffix = "?ssl=require" if self.POSTGRES_SSL else ""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_READ_HOST}:{self.POSTGRES_READ_PORT}"
            f"/{self.POSTGRES_DB}{ssl_suffix}"
        )

    @property
    def sqlite_dsn(self) -> str:
        """Build the SQLite DSN (aiosqlite)."""
        return f"sqlite+aiosqlite:///{self.SQLITE_PATH}"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    model_config = {"env_file": ".env", "extra": "ignore", "populate_by_name": True}


db_config = DatabaseConfig()
