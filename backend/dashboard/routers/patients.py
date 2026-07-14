"""
HELIOS OS + SEVRA AI
Patient APIs (Section 4)
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from dashboard.schemas.api import (
    PaginatedResponse, 
    PatientResponse, 
    PatientSummaryResponse,
    VitalResponse,
    AlertResponse,
    PredictionResponse
)
from dashboard.api.dependencies import get_uow, get_current_user, PaginationParams, require_role
from database.services.uow import UnitOfWork
from database.services.queries import QueryService

router = APIRouter()

@router.get("", response_model=PaginatedResponse[PatientResponse], dependencies=[Depends(require_role(["Admin", "Doctor", "Nurse"]))])
async def get_patients(
    pagination: PaginationParams = Depends(),
    uow: UnitOfWork = Depends(get_uow)
):
    """Get list of patients with pagination."""
    patients = await uow.patients.get_multi(skip=pagination.skip, limit=pagination.limit)
    total = await uow.patients.count()
    return PaginatedResponse(
        items=[PatientResponse.model_validate(p) for p in patients],
        total=total,
        page=(pagination.skip // pagination.limit) + 1,
        size=pagination.limit,
        has_next=(pagination.skip + pagination.limit) < total
    )

@router.get("/{patient_id}", response_model=PatientResponse, dependencies=[Depends(require_role(["Admin", "Doctor", "Nurse"]))])
async def get_patient(
    patient_id: str,
    uow: UnitOfWork = Depends(get_uow)
):
    """Get single patient details."""
    patient = await uow.patients.get_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return PatientResponse.model_validate(patient)

@router.get("/{patient_id}/summary", response_model=PatientSummaryResponse, dependencies=[Depends(require_role(["Admin", "Doctor"]))])
async def get_patient_summary(
    patient_id: str,
    uow: UnitOfWork = Depends(get_uow)
):
    """Get comprehensive patient overview."""
    patient = await uow.patients.get_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    alerts = await uow.alerts.get_active_alerts_for_patient(patient_id)
    
    # In production, we'd fetch latest vitals and predictions optimally via QueryService or Cache
    return PatientSummaryResponse(
        patient=PatientResponse.model_validate(patient),
        active_alerts=[AlertResponse.model_validate(a) for a in alerts],
        latest_vitals={}, # Placeholder for map of metric -> vital
        latest_predictions=[]
    )
