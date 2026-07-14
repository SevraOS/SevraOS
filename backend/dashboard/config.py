"""
HELIOS OS + SEVRA AI
Dashboard Configuration
"""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings

class DashboardConfig(BaseSettings):
    """Dashboard API Configuration."""
    
    API_TITLE: str = "HELIOS Dashboard API"
    API_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    
    # CORS
    CORS_ORIGINS: List[str] = Field(default=["*"], alias="HELIOS_CORS_ORIGINS")
    
    # Security
    JWT_SECRET_KEY: str = Field("change-this-in-production-immediately", alias="HELIOS_JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    
    # Redis for Pub/Sub
    REDIS_URL: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    
    # Pagination Defaults
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 1000

    model_config = {"env_file": ".env", "extra": "ignore", "populate_by_name": True}

dash_config = DashboardConfig()
