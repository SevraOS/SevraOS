"""
HELIOS OS + SEVRA AI
Object Storage Archive Service - SECTION 17
"""

import json
import structlog
from typing import Any, Dict
from datetime import datetime, timezone
import aioboto3

from database.config.settings import db_config

logger = structlog.get_logger(__name__)

class ArchiveService:
    """
    Handles Tier 3 storage (Object Storage via MinIO/S3).
    Used for archiving old vitals, waveforms, and audit logs.
    """
    
    def __init__(self):
        self.session = aioboto3.Session()
        self.client_kwargs = {
            "service_name": "s3",
            "endpoint_url": f"http://{db_config.MINIO_ENDPOINT}" if not db_config.MINIO_SECURE else f"https://{db_config.MINIO_ENDPOINT}",
            "aws_access_key_id": db_config.MINIO_ACCESS_KEY,
            "aws_secret_access_key": db_config.MINIO_SECRET_KEY,
        }

    async def _ensure_bucket(self, client: Any, bucket_name: str) -> None:
        try:
            await client.head_bucket(Bucket=bucket_name)
        except Exception as e:
            # Depending on the exception, it might mean it doesn't exist.
            # In a real app we'd check error codes (e.g. 404). For now, just try to create.
            try:
                await client.create_bucket(Bucket=bucket_name)
                logger.info("minio_bucket_created", bucket=bucket_name)
            except Exception as create_e:
                logger.debug("minio_bucket_create_skipped", error=str(create_e))

    async def archive_vitals_batch(self, patient_id: str, date_str: str, vitals_list: list[Dict]) -> str:
        """
        Archive a batch of vitals as a compressed JSONL file (NDJSON).
        Path: /<patient_id>/<year>/<month>/vitals_<date>.jsonl
        """
        bucket = db_config.MINIO_BUCKET_VITALS
        object_name = f"{patient_id}/{date_str[:4]}/{date_str[5:7]}/vitals_{date_str}.jsonl"
        
        # Convert to NDJSON
        payload = "\n".join([json.dumps(v) for v in vitals_list]).encode('utf-8')
        
        async with self.session.client(**self.client_kwargs) as s3:
            await self._ensure_bucket(s3, bucket)
            await s3.put_object(
                Bucket=bucket,
                Key=object_name,
                Body=payload,
                ContentType='application/x-ndjson'
            )
            
        logger.info("vitals_archived", patient=patient_id, count=len(vitals_list), path=object_name)
        return object_name

    async def store_waveform(self, device_id: str, timestamp: datetime, payload: bytes, format: str = "edf") -> str:
        """
        Store raw waveform data (ECG, EEG, etc.).
        """
        bucket = db_config.MINIO_BUCKET_WAVEFORMS
        date_path = timestamp.strftime("%Y/%m/%d")
        file_name = timestamp.strftime("%H%M%S")
        object_name = f"{device_id}/{date_path}/{file_name}.{format}"
        
        async with self.session.client(**self.client_kwargs) as s3:
            await self._ensure_bucket(s3, bucket)
            await s3.put_object(
                Bucket=bucket,
                Key=object_name,
                Body=payload,
                ContentType='application/octet-stream'
            )
            
        logger.debug("waveform_stored", device=device_id, path=object_name)
        return object_name
