"""
HELIOS OS + SEVRA AI
Dashboard API Entrypoint (Section 3)
"""

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dashboard.config import dash_config
from dashboard.routers import patients, devices, vitals, alerts, predictions, ws
from dashboard.websocket.manager import ws_manager
import asyncio

logger = structlog.get_logger(__name__)

import os
from contextlib import asynccontextmanager
from database.services.connection import db_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("dashboard_api_starting")
    dsn = os.environ.get("HELIOS_POSTGRES_DSN")
    if dsn:
        db_manager.initialize_postgres(dsn)
    ws_task = asyncio.create_task(ws_manager.start_redis_listener())
    yield
    # Shutdown
    logger.info("dashboard_api_shutting_down")
    ws_task.cancel()

app = FastAPI(
    title=dash_config.API_TITLE,
    version=dash_config.API_VERSION,
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=dash_config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST Routers
app.include_router(patients.router, prefix=dash_config.API_PREFIX + "/patients", tags=["Patients"])
app.include_router(devices.router, prefix=dash_config.API_PREFIX + "/devices", tags=["Devices"])
app.include_router(vitals.router, prefix=dash_config.API_PREFIX + "/vitals", tags=["Vitals"])
app.include_router(alerts.router, prefix=dash_config.API_PREFIX + "/alerts", tags=["Alerts"])
app.include_router(predictions.router, prefix=dash_config.API_PREFIX + "/predictions", tags=["Predictions"])
app.include_router(ws.router, prefix="/ws", tags=["WebSockets"])

@app.get("/health", tags=["System Health"])
async def health_check():
    """System Health Endpoint"""
    return {"status": "ok", "service": "dashboard"}
