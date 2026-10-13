from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import Settings


class MongoClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncIOMotorClient(settings.mongo_uri)

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._client[self._settings.mongo_db]

    async def ping(self) -> bool:
        try:
            await self.db.command("ping")
        except Exception:  # noqa: BLE001
            return False
        return True

    async def close(self) -> None:
        self._client.close()
