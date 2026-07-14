"""
HELIOS OS + SEVRA AI
Epic Hospital Adapter (Section 6)
"""

import httpx
import structlog
from typing import Dict, Any

from integration.config import integration_config
from integration.fhir.models import Observation

logger = structlog.get_logger(__name__)

class EpicAdapter:
    """Client for Epic Interconnect FHIR APIs."""
    
    def __init__(self):
        self.base_url = integration_config.FHIR_BASE_URL
        self.client_id = integration_config.CLIENT_ID
        self.secret = integration_config.CLIENT_SECRET
        self.token = None
        
    async def authenticate(self) -> str:
        """Authenticate using Epic's OAuth2 client credentials flow."""
        # Simplified for demo
        self.token = "mock_epic_oauth_token_123"
        logger.info("epic_adapter_authenticated")
        return self.token
        
    async def push_observation(self, observation: Observation) -> bool:
        """Push a vital sign or risk score to Epic."""
        if not self.token:
            await self.authenticate()
            
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json"
        }
        
        payload = observation.model_dump(exclude_none=True)
        # Convert datetime to string for JSON serialization
        payload["effectiveDateTime"] = payload["effectiveDateTime"].isoformat()
        
        # Using async client to prevent blocking
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/Observation",
                    json=payload,
                    headers=headers,
                    timeout=5.0
                )
                
                if response.status_code in (200, 201):
                    logger.info("epic_push_success", resource="Observation")
                    return True
                else:
                    logger.error("epic_push_failed", status=response.status_code, response=response.text)
                    return False
            except httpx.RequestError as e:
                logger.error("epic_connection_error", error=str(e))
                return False
