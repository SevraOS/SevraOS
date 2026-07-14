"""
HELIOS OS + SEVRA AI
Device Repository
"""

from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models.device import Device
from database.repositories.base import BaseRepository


class DeviceRepository(BaseRepository[Device]):
    def __init__(self, session: AsyncSession):
        super().__init__(Device, session)

    async def get_by_device_id(self, device_id: str) -> Optional[Device]:
        """Fetch a device by its unique hardware ID."""
        stmt = select(Device).where(Device.device_id == device_id).where(Device.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_devices_by_patient(self, patient_id: str) -> Sequence[Device]:
        """Get all active devices currently assigned to a patient."""
        stmt = (
            select(Device)
            .where(Device.assigned_patient_id == patient_id)
            .where(Device.is_active.is_(True))
            .where(Device.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
