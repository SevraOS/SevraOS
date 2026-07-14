"""
HELIOS OS + SEVRA AI
AI Service Configuration
"""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings

class AIConfig(BaseSettings):
    """AI Service Configuration."""
    
    ENVIRONMENT: str = Field("development", alias="HELIOS_ENVIRONMENT")
    
    # ONNX Runtime
    ONNX_EXECUTION_PROVIDERS: List[str] = Field(
        default=["CPUExecutionProvider"], # E.g., 'CUDAExecutionProvider' for GPU
        alias="HELIOS_ONNX_PROVIDERS"
    )
    MODELS_DIR: str = Field("./ai/models/assets", alias="HELIOS_MODELS_DIR")
    
    # Consumer Settings
    CONSUMER_BATCH_SIZE: int = Field(50, alias="HELIOS_AI_CONSUMER_BATCH")
    CONSUMER_BLOCK_MS: int = Field(2000, alias="HELIOS_AI_CONSUMER_BLOCK")
    
    # Redis
    REDIS_URL: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    
    # Thresholds
    CRITICAL_RISK_THRESHOLD: float = 0.85
    HIGH_RISK_THRESHOLD: float = 0.70

    model_config = {"env_file": ".env", "extra": "ignore", "populate_by_name": True}

ai_config = AIConfig()
