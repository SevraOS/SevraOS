"""
HELIOS OS + SEVRA AI
Query Services - SECTION 18
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from database.services.uow import UnitOfWork

class QueryService:
    """
    High-level query services for Dashboards and Reports.
    Wraps Repository calls into business logic operations.
    """
    
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    async def get_patient_timeline(
        self, 
        patient_id: str, 
        start_time: datetime, 
        end_time: datetime,
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Retrieve a combined timeline of Vitals, Alerts, and Predictions.
        """
        async with self.uow_factory() as uow:
            # We run these concurrently for performance in a real app, 
            # here we execute sequentially for clarity within the UoW
            
            vitals = await uow.vitals.get_patient_timeline(
                patient_id, start_time, end_time, metrics=metrics
            )
            
            # Use raw select for alerts within time range since repo doesn't have time bound method
            # (In production, we'd add the specific method to AlertRepository)
            from sqlalchemy import select
            from database.models.alert import Alert
            from database.models.prediction import Prediction
            
            alert_stmt = select(Alert).where(
                Alert.patient_id == patient_id,
                Alert.created_at >= start_time,
                Alert.created_at <= end_time
            )
            alerts = (await uow.session.execute(alert_stmt)).scalars().all()
            
            pred_stmt = select(Prediction).where(
                Prediction.patient_id == patient_id,
                Prediction.created_at >= start_time,
                Prediction.created_at <= end_time
            )
            predictions = (await uow.session.execute(pred_stmt)).scalars().all()

            return {
                "patient_id": patient_id,
                "period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "vitals_count": len(vitals),
                "vitals": [v.to_dict() for v in vitals],
                "alerts": [a.to_dict() for a in alerts],
                "predictions": [p.to_dict() for p in predictions]
            }

    async def get_active_alerts_summary(self) -> Dict[str, Any]:
        """
        Get a system-wide summary of unacknowledged alerts grouped by severity.
        """
        async with self.uow_factory() as uow:
            alerts = await uow.alerts.get_unacknowledged_alerts(limit=500)
            
            summary = {
                "CRITICAL": 0,
                "HIGH": 0,
                "MEDIUM": 0,
                "LOW": 0,
                "INFO": 0,
                "total": len(alerts),
                "oldest_unacknowledged": None
            }
            
            if alerts:
                # Assuming ordered by created_at desc from repo
                summary["oldest_unacknowledged"] = alerts[-1].created_at.isoformat()
                
            for a in alerts:
                if a.severity in summary:
                    summary[a.severity] += 1
                    
            return summary

    async def get_historical_trends(self, patient_id: str, metric: str, days: int = 30) -> Dict[str, Any]:
        """
        Historical Trends Query (Section 18).
        Aggregates data over a longer time range.
        """
        async with self.uow_factory() as uow:
            # In a real app, this would use SQL aggregation (AVG, MIN, MAX over windows)
            # For demonstration, we'll fetch via the repository.
            # Assuming a custom repository method or raw SQL for actual aggregation.
            return {
                "patient_id": patient_id,
                "metric": metric,
                "trend": "calculated_trend_data",
                "period_days": days
            }

    async def get_prediction_history(self, patient_id: str, prediction_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Prediction History Query (Section 18).
        """
        async with self.uow_factory() as uow:
            predictions = await uow.predictions.get_prediction_history(patient_id, prediction_type, limit)
            return [p.to_dict() for p in predictions]
