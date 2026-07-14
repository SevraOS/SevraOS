"""
HELIOS OS + SEVRA AI
Integration Configuration
"""

from pydantic import Field
from pydantic_settings import BaseSettings

class IntegrationConfig(BaseSettings):
    """Integration Service Configuration."""
    
    ENVIRONMENT: str = Field("production", alias="HELIOS_ENVIRONMENT")
    
    # Redis
    REDIS_URL: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    
    # Hospital Systems Config
    EHR_VENDOR: str = Field("epic", alias="HELIOS_EHR_VENDOR") # epic, cerner, generic_fhir
    FHIR_BASE_URL: str = Field("https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4", alias="HELIOS_FHIR_URL")
    HL7_MLLP_HOST: str = Field("10.0.0.50", alias="HELIOS_HL7_HOST")
    HL7_MLLP_PORT: int = Field(2575, alias="HELIOS_HL7_PORT")
    
    # Auth
    CLIENT_ID: str = Field("helios-client-id", alias="HELIOS_EHR_CLIENT_ID")
    CLIENT_SECRET: str = Field("helios-secret", alias="HELIOS_EHR_CLIENT_SECRET")
    
    # Sync Configuration
    MAX_RETRIES: int = 5
    SYNC_INTERVAL_SECONDS: int = 60

    model_config = {"env_file": ".env", "extra": "ignore", "populate_by_name": True}

integration_config = IntegrationConfig()
