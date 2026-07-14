"""
HELIOS OS + SEVRA AI
Conflict Resolution - SECTION 12
"""

import structlog
from typing import Dict, Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.vital import Vital
from database.models.alert import Alert
from database.models.base import SyncStatus

logger = structlog.get_logger(__name__)

class ConflictResolver:
    """
    Handles SQLite -> PostgreSQL sync conflicts.
    Follows Section 5.6: UPSERT with Idempotent Merge.
    Clinical data fields are NEVER overwritten — only metadata is updated.
    """

    @staticmethod
    async def upsert_vital(session: AsyncSession, vital_dict: Dict[str, Any]) -> None:
        """
        Upsert a vital record into PostgreSQL.
        ON CONFLICT (client_event_id): update metadata, mark as synced.
        """
        stmt = insert(Vital).values(**vital_dict)
        
        # Conflict resolution strategy
        do_update_stmt = stmt.on_conflict_do_update(
            index_elements=["client_event_id"],
            set_=dict(
                updated_at=stmt.excluded.updated_at,
                metadata_payload=stmt.excluded.metadata_payload,
                # Force status to SYNCED since it's now in PG
                sync_status=SyncStatus.SYNCED.value,
                # Do NOT overwrite metric, value, unit, loinc, captured_at
            )
        )
        
        await session.execute(do_update_stmt)

    @staticmethod
    async def upsert_alert(session: AsyncSession, alert_dict: Dict[str, Any]) -> None:
        """
        Upsert an alert.
        ON CONFLICT (client_event_id): update acknowledgment status and metadata.
        """
        stmt = insert(Alert).values(**alert_dict)
        
        do_update_stmt = stmt.on_conflict_do_update(
            index_elements=["client_event_id"],
            set_=dict(
                updated_at=stmt.excluded.updated_at,
                is_acknowledged=stmt.excluded.is_acknowledged,
                acknowledged_by=stmt.excluded.acknowledged_by,
                acknowledged_at=stmt.excluded.acknowledged_at,
                resolved=stmt.excluded.resolved,
                resolved_at=stmt.excluded.resolved_at,
                metadata_payload=stmt.excluded.metadata_payload,
                sync_status=SyncStatus.SYNCED.value,
            )
        )
        
        await session.execute(do_update_stmt)
