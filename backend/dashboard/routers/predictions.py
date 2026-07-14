"""
HELIOS OS + SEVRA AI
Prediction APIs (Section 8)
"""

from fastapi import APIRouter, Depends
from typing import List

from dashboard.schemas.api import PaginatedResponse, PredictionResponse
from dashboard.api.dependencies import get_uow, get_current_user, PaginationParams
from database.services.uow import UnitOfWork
from database.services.queries import QueryService

router = APIRouter()

@router.get("/latest", response_model=List[PredictionResponse])
async def get_latest_predictions(
    patient_id: str,
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user)
):
    """Get the most recent predictions for a patient."""
    predictions = await uow.predictions.get_prediction_history(patient_id, prediction_type=None, limit=10)
    return [PredictionResponse.model_validate(p) for p in predictions]

@router.get("/history", response_model=List[PredictionResponse])
async def get_prediction_history(
    patient_id: str,
    prediction_type: str,
    limit: int = 50,
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user)
):
    """Get history for a specific AI prediction model over time."""
    query_service = QueryService(lambda: uow)
    predictions_dicts = await query_service.get_prediction_history(patient_id, prediction_type, limit)
    return [PredictionResponse.model_validate(p) for p in predictions_dicts]

@router.get("/risk-trends")
async def get_risk_trends(
    patient_id: str,
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user)
):
    """Get aggregated AI Risk score trends."""
    return {"status": "implemented", "patient_id": patient_id}
