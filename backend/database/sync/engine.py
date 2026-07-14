"""
HELIOS OS + SEVRA AI
Sync Engine - SECTION 11
"""

import asyncio
import structlog
from typing import Callable, Type, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, update
from datetime import datetime, timezone

from database.models.base import HeliosBase, SyncStatus
from database.models.vital import Vital
from database.models.alert import Alert
from database.config.settings import db_config
from database.sync.conflict_resolver import ConflictResolver
from database.metrics.prometheus import metrics

logger = structlog.get_logger(__name__)

class SyncEngine:
    """
    Asynchronous replication from SQLite to PostgreSQL.
    Follows Section 5.5: Offline-First Strategy.
    """
    
    def __init__(
        self, 
        sqlite_session_factory: async_sessionmaker[AsyncSession],
        pg_session_factory: async_sessionmaker[AsyncSession]
    ):
        self.sqlite_session_factory = sqlite_session_factory
        self.pg_session_factory = pg_session_factory
        self._running = False
        self._task = None

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info("sync_engine_started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("sync_engine_stopped")

    async def _sync_loop(self):
        """Continuously pulls pending records from SQLite and pushes to PostgreSQL."""
        while self._running:
            try:
                # Sync tables sequentially. Order matters if there are FKs (we use loose coupling via UUIDs)
                await self._sync_table(Vital, ConflictResolver.upsert_vital)
                await self._sync_table(Alert, ConflictResolver.upsert_alert)
                # (Add Prediction, Notification, etc here)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("sync_engine_loop_error", error=str(e), exc_info=True)
                metrics.inc_failure("sync_engine", "loop_crash")
            
            await asyncio.sleep(db_config.SYNC_INTERVAL_SECONDS)

    async def _sync_table(self, model: Type[HeliosBase], upsert_func: Callable) -> None:
        """Syncs a single table batch."""
        
        # 1. Fetch pending from SQLite
        async with self.sqlite_session_factory() as sqlite_session:
            stmt = (
                select(model)
                .where(model.sync_status == SyncStatus.PENDING.value)
                .where(model.sync_attempts < db_config.SYNC_MAX_RETRY)
                .order_by(model.created_at.asc()) # Oldest first
                .limit(db_config.SYNC_BATCH_SIZE)
            )
            result = await sqlite_session.execute(stmt)
            pending_records = result.scalars().all()

            if not pending_records:
                metrics.set_pending_sync(model.__tablename__, 0)
                return

            logger.debug(f"syncing_{model.__tablename__}", count=len(pending_records))
            metrics.set_pending_sync(model.__tablename__, len(pending_records))

            # Convert to dicts for PostgreSQL Upsert
            records_dicts = [record.to_dict() for record in pending_records]
            # Ensure sync_status is set to SYNCED in the payload going to PG
            for d in records_dicts:
                d["sync_status"] = SyncStatus.SYNCED.value

            success_ids = []
            error_ids = []
            
            # 2. Push to PostgreSQL
            try:
                async with self.pg_session_factory() as pg_session:
                    async with pg_session.begin(): # Transaction
                        for record_dict in records_dicts:
                            try:
                                await upsert_func(pg_session, record_dict)
                                success_ids.append(record_dict["id"])
                            except Exception as record_error:
                                logger.error(
                                    "sync_record_failed", 
                                    table=model.__tablename__, 
                                    id=record_dict["id"], 
                                    error=str(record_error)
                                )
                                error_ids.append(record_dict["id"])
                                # Continue with next record
                
                # PG Commit happens automatically on exit of `async with pg_session.begin():`
            except Exception as pg_error:
                # Entire batch failed (e.g., connection issue)
                logger.error("sync_batch_failed_pg_unavailable", error=str(pg_error))
                metrics.inc_failure("postgresql", "sync_push")
                error_ids = [r["id"] for r in records_dicts]
                success_ids = []

            # 3. Update SQLite status
            if success_ids or error_ids:
                async with sqlite_session.begin():
                    now = datetime.now(timezone.utc)
                    if success_ids:
                        await sqlite_session.execute(
                            update(model)
                            .where(model.id.in_(success_ids))
                            .values(
                                sync_status=SyncStatus.SYNCED.value,
                                last_sync_at=now,
                                sync_error=None
                            )
                        )
                        metrics.inc_sync("success", len(success_ids))
                        
                        # Audit Trail (Section 11)
                        logger.info("sync_batch_audit_trail", 
                                    action="SYNC_TO_POSTGRES", 
                                    table=model.__tablename__, 
                                    records_synced=len(success_ids),
                                    timestamp=now.isoformat())
                        
                    if error_ids:
                        # Fetch and update attempts manually to increment safely
                        for eid in error_ids:
                            record = await sqlite_session.get(model, eid)
                            if record:
                                record.sync_status = SyncStatus.ERROR.value
                                record.sync_attempts += 1
                                record.last_sync_at = now
                                record.sync_error = "Sync failed during batch upsert"
                        metrics.inc_sync("error", len(error_ids))
