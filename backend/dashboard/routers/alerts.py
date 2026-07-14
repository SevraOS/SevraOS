"""
HELIOS OS + SEVRA AI
Alerts APIs (Section 7)
"""

from fastapi import APIRouter, Depends
from typing import List

from dashboard.schemas.api import PaginatedResponse, AlertResponse
from dashboard.api.dependencies import get_uow, get_current_user, PaginationParams
from database.services.uow import UnitOfWork
from database.services.queries import QueryService

router = APIRouter()

@router.get("/active", response_model=List[AlertResponse])
async def get_active_alerts(
    patient_id: str = None,
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user)
):
    """Get currently active, unacknowledged alerts."""
    if patient_id:
        alerts = await uow.alerts.get_active_alerts_for_patient(patient_id)
    else:
        alerts = [] # Needs global active alerts implementation
    return [AlertResponse.model_validate(a) for a in alerts]

@router.get("/history", response_model=PaginatedResponse[AlertResponse])
async def get_alert_history(
    pagination: PaginationParams = Depends(),
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user)
):
    """Get complete alert history."""
    alerts = await uow.alerts.get_multi(skip=pagination.skip, limit=pagination.limit)
    total = await uow.alerts.count()
    return PaginatedResponse(
        items=[AlertResponse.model_validate(a) for a in alerts],
        total=total,
        page=(pagination.skip // pagination.limit) + 1,
        size=pagination.limit,
        has_next=(pagination.skip + pagination.limit) < total
    )

@router.get("/statistics")
async def get_alert_statistics(
    patient_id: str = None,
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user)
):
    """Get aggregated alert counts by severity."""
    query_service = QueryService(lambda: uow)
    return await query_service.get_alert_summary(patient_id)
