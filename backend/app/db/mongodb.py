from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from ..core.config import MONGO_DB_NAME, MONGO_URI

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URI)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[MONGO_DB_NAME]


async def init_indexes() -> None:
    db = get_db()
    await db.users.create_index("email", unique=True)
    await db.song_analyses.create_index("user_id")
    await db.song_analyses.create_index("created_at")
