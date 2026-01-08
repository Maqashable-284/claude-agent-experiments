"""
MongoDB Database Connection Manager.
Adapted from Scoop AI V7 for the Claude Agent SDK project.
"""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages MongoDB connections with lazy initialization."""
    
    def __init__(self):
        self._client: Optional[AsyncIOMotorClient] = None
        self._database: Optional[AsyncIOMotorDatabase] = None
        self._initialized = False
    
    @property
    def is_connected(self) -> bool:
        return self._initialized and self._client is not None
    
    async def connect(self, uri: str, db_name: str) -> None:
        """Establish database connection."""
        if self._initialized:
            return
        
        self._client = AsyncIOMotorClient(
            uri,
            minPoolSize=1,
            maxPoolSize=10,
            connectTimeoutMS=5000,
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=10000,
            retryWrites=True,
            retryReads=True,
        )
        
        self._database = self._client[db_name]
        
        # Verify connection
        try:
            await self._client.admin.command("ping")
            self._initialized = True
            logger.info(f"MongoDB connected: {db_name}")
        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            if self._client:
                self._client.close()
                self._client = None
                self._database = None
            raise
    
    async def disconnect(self) -> None:
        """Close database connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
            self._initialized = False
            logger.info("MongoDB disconnected")
    
    async def get_database(self) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if not self._initialized or self._database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._database
    
    async def ping(self) -> bool:
        """Health check."""
        if not self._initialized or not self._client:
            return False
        try:
            await self._client.admin.command("ping")
            return True
        except:
            return False


# Global instance
db_manager = DatabaseManager()


async def get_db() -> AsyncIOMotorDatabase:
    """FastAPI dependency for database access."""
    return await db_manager.get_database()
