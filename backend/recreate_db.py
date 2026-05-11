import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.database import Base
from app.models.orm import TaskRecord

DATABASE_URL = "sqlite+aiosqlite:///./aegis.db"
engine = create_async_engine(DATABASE_URL, echo=True)

async def recreate():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Database recreated successfully.")

asyncio.run(recreate())
