import os
from pydantic import Field
from pydantic_settings import BaseSettings

class EventBusConfig(BaseSettings):
    """Configuration for the Redis Event Bus"""
    REDIS_URL: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    REDIS_POOL_SIZE: int = Field(100, env="REDIS_POOL_SIZE")
    REDIS_TIMEOUT: float = Field(5.0, env="REDIS_TIMEOUT")
    
    # Retry logic
    RETRY_MAX_ATTEMPTS: int = Field(3, env="EVENTBUS_MAX_RETRIES")
    RETRY_BASE_DELAY: float = Field(1.0, env="EVENTBUS_RETRY_BASE_DELAY")
    
    # DLQ Config
    DLQ_STREAM_NAME: str = Field("sevra:dlq", env="EVENTBUS_DLQ_STREAM")
    
    # Local buffering (Offline first)
    ENABLE_LOCAL_BUFFER: bool = Field(True, env="EVENTBUS_ENABLE_LOCAL_BUFFER")
    LOCAL_BUFFER_PATH: str = Field(".buffer/eventbus", env="EVENTBUS_LOCAL_BUFFER_PATH")

    class Config:
        env_file = ".env"
        extra = "ignore"

config = EventBusConfig()
