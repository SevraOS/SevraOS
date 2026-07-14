"""
HELIOS OS + SEVRA AI
Redis Cache Layer - SECTION 13
"""

import json
import structlog
from typing import Optional, Any, Dict
from eventbus.client import RedisClientManager
from database.config.settings import db_config
from database.metrics.prometheus import metrics

logger = structlog.get_logger(__name__)

class CacheManager:
    """
    Manages Redis caching for Tier 4 Operational Data.
    Follows Section 13: Support Latest Vitals, Patient Summary, Device Status.
    """
    
    def __init__(self):
        self.prefix = db_config.REDIS_CACHE_PREFIX
        self.ttl = db_config.REDIS_CACHE_TTL

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store JSON serializable data in cache."""
        try:
            client = RedisClientManager.get_client()
            full_key = f"{self.prefix}{key}"
            payload = json.dumps(value)
            expire_time = ttl if ttl is not None else self.ttl
            
            await client.set(full_key, payload, ex=expire_time)
        except Exception as e:
            # Cache failure should not crash the app
            logger.error("cache_set_failed", key=key, error=str(e))

    async def get(self, key: str, entity_type: str = "generic") -> Optional[Any]:
        """Retrieve and deserialize data from cache."""
        try:
            client = RedisClientManager.get_client()
            full_key = f"{self.prefix}{key}"
            
            payload = await client.get(full_key)
            if payload:
                metrics.inc_cache_hit(entity_type)
                return json.loads(payload)
            else:
                metrics.inc_cache_miss(entity_type)
                return None
                
        except Exception as e:
            logger.error("cache_get_failed", key=key, error=str(e))
            metrics.inc_cache_miss(entity_type)
            return None

    async def invalidate(self, key: str) -> None:
        """Remove an item from the cache."""
        try:
            client = RedisClientManager.get_client()
            full_key = f"{self.prefix}{key}"
            await client.delete(full_key)
        except Exception as e:
            logger.error("cache_invalidate_failed", key=key, error=str(e))

    # --- Specific Domain Cache Methods ---

    async def set_latest_vital(self, patient_id: str, metric: str, vital_dict: Dict) -> None:
        key = f"vital:latest:{patient_id}:{metric}"
        # Vitals change fast, keep TTL short or explicitly invalidate
        await self.set(key, vital_dict, ttl=600)

    async def get_latest_vital(self, patient_id: str, metric: str) -> Optional[Dict]:
        key = f"vital:latest:{patient_id}:{metric}"
        return await self.get(key, entity_type="vital")

    async def set_patient_summary(self, patient_id: str, summary_dict: Dict) -> None:
        key = f"patient:summary:{patient_id}"
        await self.set(key, summary_dict, ttl=3600)

    async def get_patient_summary(self, patient_id: str) -> Optional[Dict]:
        key = f"patient:summary:{patient_id}"
        return await self.get(key, entity_type="patient")

    async def set_device_status(self, device_id: str, status_dict: Dict) -> None:
        key = f"device:status:{device_id}"
        await self.set(key, status_dict, ttl=300)

