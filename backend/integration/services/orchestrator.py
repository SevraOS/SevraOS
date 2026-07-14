"""
HELIOS OS + SEVRA AI
Integration Service Orchestrator (Section 1)
"""

import structlog
from integration.sync.engine import SyncEngine

logger = structlog.get_logger(__name__)

class IntegrationOrchestrator:
    """Central service bridging the Redis Event Bus with the Sync Engine."""
    
    def __init__(self):
        self.engine = SyncEngine()
        
    async def process_batch(self, events: list):
        """Process a batch of CanonicalEvents from Redis and push to hospital."""
        logger.info("integration_orchestrator_processing", batch_size=len(events))
        await self.engine.sync_vitals_to_ehr(events)
