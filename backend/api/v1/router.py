"""
HELIOS OS + SEVRA AI
API v1 Router

All v1 endpoints are registered here.
Future modules add their router with include_router — no modification of existing code.
"""

from fastapi import APIRouter

from api.v1.endpoints.health import router as health_router

from config.settings import get_settings

settings = get_settings()

v1_router = APIRouter(prefix=settings.API_V1_PREFIX)

# ── Foundation Endpoints ─────────────────────────────────────────────────────
v1_router.include_router(health_router, prefix="/health", tags=["Health"])

# ── Dashboard Endpoints (Compatibility) ────────────────────────────────────
from dashboard.routers import patients, devices, vitals, alerts, predictions, ws

v1_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
v1_router.include_router(devices.router, prefix="/devices", tags=["Devices"])
v1_router.include_router(vitals.router, prefix="/vitals", tags=["Vitals"])
v1_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
v1_router.include_router(predictions.router, prefix="/predictions", tags=["Predictions"])
v1_router.include_router(ws.router, prefix="/ws", tags=["WebSockets"])
