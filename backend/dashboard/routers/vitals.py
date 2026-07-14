"""
HELIOS OS + SEVRA AI
Vitals APIs (Section 6)
"""

from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta
from typing import List, Optional

from dashboard.schemas.api import VitalResponse
from dashboard.api.dependencies import get_uow, get_current_user
from database.services.uow import UnitOfWork
from database.services.queries import QueryService

router = APIRouter()

@router.get("/latest", response_model=List[VitalResponse])
async def get_latest_vitals(
    patient_id: str,
    metrics: Optional[List[str]] = Query(None),
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user)
):
    """Get the latest reading for given metrics."""
    # Would typically consult the Redis Cache layer here first
    # Fallback to DB
    return []

@router.get("/history", response_model=List[VitalResponse])
async def get_historical_vitals(
    patient_id: str,
    start_time: datetime,
    end_time: datetime,
    metrics: Optional[List[str]] = Query(None),
    limit: int = 1000,
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user)
):
    """Get time-series history for chart rendering."""
    vitals = await uow.vitals.get_patient_timeline(
        patient_id=patient_id,
        start_time=start_time,
        end_time=end_time,
        metrics=metrics,
        limit=limit
    )
    return [VitalResponse.model_validate(v) for v in vitals]

@router.get("/trends")
async def get_vital_trends(
    patient_id: str,
    metric: str,
    days: int = 30,
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user)
):
    """Get aggregated trend analysis over long periods."""
    query_service = QueryService(lambda: uow)
    return await query_service.get_historical_trends(patient_id, metric, days)
