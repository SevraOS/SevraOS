"""
Alembic migration environment script.
Handles async SQLAlchemy engine for PostgreSQL migrations.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Load config
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the PostgreSQL URL from environment variables
def get_url() -> str:
    # Use DSN directly if available (from Docker environment)
    dsn = os.environ.get("HELIOS_POSTGRES_DSN")
    if dsn:
        return dsn
    # Fallback to individual variables
    user = os.environ.get("HELIOS_POSTGRES_USER", "helios")
    password = os.environ.get("HELIOS_POSTGRES_PASSWORD", "helios_dev_password")
    host = os.environ.get("HELIOS_POSTGRES_HOST", "localhost")
    port = os.environ.get("HELIOS_POSTGRES_PORT", "5432")
    db = os.environ.get("HELIOS_POSTGRES_DB", "helios")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


from database.models.base import HeliosBase
# Import ALL models so Alembic detects the full schema:
from database.models.patient import Patient
from database.models.vital import Vital
from database.models.alert import Alert
from database.models.device import Device
from database.models.prediction import Prediction
from database.models.audit_log import AuditLog
from database.models.notification import Notification
from database.models.rejected_reading import RejectedReading
from database.models.sync_queue import HospitalSyncQueue
from database.models.system_event import SystemEvent

target_metadata = HeliosBase.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode (no DB connection required)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)  # type: ignore[arg-type]
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations with an async SQLAlchemy engine."""
    engine = create_async_engine(get_url())
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
