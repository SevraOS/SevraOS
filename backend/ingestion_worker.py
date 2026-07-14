import asyncio
import json
import uuid
import os
import redis.asyncio as redis_async
import redis.exceptions
from datetime import datetime, timezone

from database.models.vital import Vital
from database.models.base import HeliosBase
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

async def main():
    print("🚀 Starting Ingestion Worker...")
    
    # Connect to PostgreSQL
    dsn = os.environ.get(
        "HELIOS_POSTGRES_DSN",
        "postgresql+asyncpg://helios:helios_dev_password@postgres:5432/helios"
    )
    engine = create_async_engine(dsn)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Connect to Redis (no password configured on the dev Redis container)
    redis_host = os.environ.get("HELIOS_REDIS_HOST", "redis")
    redis_port = int(os.environ.get("HELIOS_REDIS_PORT", "6379"))
    redis_password = os.environ.get("HELIOS_REDIS_PASSWORD") or None
    r = redis_async.Redis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True)
    try:
        await r.ping()
        print("✅ Connected to Redis!")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        raise

    # Ensure stream group exists
    try:
        await r.xgroup_create("helios.telemetry.raw", "ingestion_group", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            pass

    print("📥 Listening for telemetry data on helios.telemetry.raw...")
    
    while True:
        try:
            messages = await r.xreadgroup("ingestion_group", "consumer-1", {"helios.telemetry.raw": ">"}, count=10, block=2000)
            if not messages:
                continue
                
            for stream, msgs in messages:
                for msg_id, msg_data in msgs:
                    payload = json.loads(msg_data["payload"])
                    
                    async with async_session() as session:
                        vital = Vital(
                            client_event_id=str(uuid.uuid4()),
                            patient_id=payload["patient_id"],
                            metric=payload["metric"],
                            value=payload["value"],
                            unit=payload["unit"],
                            loinc="8867-4", # Default HR LOINC
                            captured_at=datetime.fromisoformat(payload["timestamp"]),
                            source_device=payload["device_id"]
                        )
                        session.add(vital)
                        await session.commit()
                        print(f"💾 Saved {payload['metric']}: {payload['value']} to PostgreSQL")
                        
                    await r.xack(stream, "ingestion_group", msg_id)
        except Exception as e:
            print(f"Error processing message: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
