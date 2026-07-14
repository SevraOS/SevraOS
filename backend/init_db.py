import asyncio
from database.models.base import HeliosBase
# Import all models to register them
from database.models import *
from sqlalchemy.ext.asyncio import create_async_engine

async def main():
    engine = create_async_engine('postgresql+asyncpg://helios:helios_dev_password@postgres:5432/helios')
    async with engine.begin() as conn:
        await conn.run_sync(HeliosBase.metadata.create_all)
    await engine.dispose()
    print("TABLES CREATED SUCCESSFULLY")

if __name__ == "__main__":
    asyncio.run(main())
