"""
HELIOS OS + SEVRA AI
Device APIs (Section 5)
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from dashboard.schemas.api import PaginatedResponse, DeviceResponse
from dashboard.api.dependencies import get_uow, get_current_user, PaginationParams
from database.services.uow import UnitOfWork

router = APIRouter()

@router.get("", response_model=PaginatedResponse[DeviceResponse])
async def get_devices(
    pagination: PaginationParams = Depends(),
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user)
):
    """Get list of devices with pagination."""
    devices = await uow.devices.get_multi(skip=pagination.skip, limit=pagination.limit)
    total = await uow.devices.count()
    return PaginatedResponse(
        items=[DeviceResponse.model_validate(d) for d in devices],
        total=total,
        page=(pagination.skip // pagination.limit) + 1,
        size=pagination.limit,
        has_next=(pagination.skip + pagination.limit) < total
    )

@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user)
):
    """Get single device details."""
    device = await uow.devices.get_by_device_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return DeviceResponse.model_validate(device)

@router.get("/status/offline", response_model=List[DeviceResponse])
async def get_offline_devices(
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user)
):
    """Get devices that have lost heartbeat connection."""
    # Simplified logic - requires proper filtering by last_seen_at < threshold
    return []
