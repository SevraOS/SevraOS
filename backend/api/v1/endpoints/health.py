"""
HELIOS OS + SEVRA AI
Health Check Endpoints

Three health endpoints following Kubernetes probe conventions:
  GET /health        — Full health with dependency status
  GET /health/ready  — Readiness probe (can accept traffic?)
  GET /health/live   — Liveness probe (is process alive?)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import ORJSONResponse

from core.monitoring.health import HealthAggregator, get_health_aggregator
from core.responses.models import HealthResponse

router = APIRouter()


@router.get(
    "",
    summary="Full system health check",
    description="Returns health status of all registered dependencies.",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
)
async def full_health(
    aggregator: HealthAggregator = Depends(get_health_aggregator),
) -> ORJSONResponse:
    """
    Full health check. Runs all registered dependency checks concurrently.
    Returns 200 for healthy/degraded, 503 for unhealthy.
    """
    health = await aggregator.run()
    http_status = (
        status.HTTP_200_OK
        if health.status in ("healthy", "degraded")
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return ORJSONResponse(
        status_code=http_status,
        content=health.model_dump(mode="json"),
    )


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Returns 200 if the service is ready to accept traffic.",
    status_code=status.HTTP_200_OK,
)
async def readiness(
    aggregator: HealthAggregator = Depends(get_health_aggregator),
) -> ORJSONResponse:
    """
    Readiness probe. Used by Kubernetes to determine if the pod should receive traffic.
    Returns 200 if healthy or degraded, 503 if unhealthy.
    """
    health = await aggregator.run()
    if health.status == "unhealthy":
        return ORJSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"ready": False, "reason": health.status},
        )
    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={"ready": True, "status": health.status},
    )


@router.get(
    "/live",
    summary="Liveness probe",
    description="Returns 200 if the process is alive (not deadlocked).",
    status_code=status.HTTP_200_OK,
)
async def liveness() -> ORJSONResponse:
    """
    Liveness probe. If this endpoint responds, the process is alive.
    Does NOT check dependencies — that is the readiness probe's job.
    """
    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={"alive": True},
    )
