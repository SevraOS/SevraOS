"""
HELIOS OS + SEVRA AI
AI Service Orchestrator (Main Entrypoint)
"""

import asyncio
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI

from ai.config import ai_config
from ai.consumers.vitals_consumer import AIVitalsConsumer
from ai.inference.onnx_runner import model_manager

logger = structlog.get_logger(__name__)

# Global instances
vitals_consumer = AIVitalsConsumer()
consumer_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global consumer_task
    
    logger.info("ai_service_starting", env=ai_config.ENVIRONMENT)
    
    # 1. Load ONNX Models
    # In production, we'd load actual models. Mocking for structural completeness.
    # model_manager.load_model("deterioration_v1", "deterioration_model_v1.onnx")
    
    # 2. Initialize Redis Streams
    await vitals_consumer.initialize()
    
    # 3. Start Background Workers
    consumer_task = asyncio.create_task(vitals_consumer.run())
    
    yield
    
    # Shutdown
    logger.info("ai_service_shutting_down")
    vitals_consumer._running = False
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="HELIOS AI Service",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    """Service Health (Section 20)"""
    return {
        "status": "ok",
        "service": "ai_inference",
        "models_loaded": len(model_manager.models),
        "consumer_running": vitals_consumer._running
    }
