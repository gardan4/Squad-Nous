import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class MongoDB:
    """Manages the async MongoDB client lifecycle."""

    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None

    async def connect(self, url: str, database: str, session_ttl: int = 3600):
        self.client = AsyncIOMotorClient(url)
        self.db = self.client[database]
        # Create indexes
        await self.db.sessions.create_index("updated_at", expireAfterSeconds=session_ttl)
        await self.db.sessions.create_index("session_id", unique=True)
        await self.db.registrations.create_index("pii_hash", unique=True)
        await self.db.registrations.create_index("schema_version")
        logger.info("MongoDB indexes created")

    async def close(self):
        if self.client:
            self.client.close()

    async def ping(self) -> bool:
        """Health check for MongoDB connection."""
        if not self.client:
            return False
        try:
            await self.client.admin.command("ping")
            return True
        except Exception:
            return False


mongodb = MongoDB()
