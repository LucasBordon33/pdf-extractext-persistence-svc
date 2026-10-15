from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.adapters.mongo.client import MongoClient
from app.adapters.mongo.document_repository import MongoDocumentRepository
from app.adapters.redis.document_cache import RedisDocumentCache
from app.api.v1.router import api_v1_router
from app.api.v1.schemas import ErrorResponse
from app.config import Settings
from app.domain.services.persistence_service import PersistenceService

INTERNAL_ERROR_CODE = "INTERNAL_ERROR"
INTERNAL_ERROR_MESSAGE = "Internal server error"


def create_app(settings: Settings) -> FastAPI:
    mongo_client = MongoClient(settings)
    repository = MongoDocumentRepository(mongo_client)
    cache = RedisDocumentCache(settings)
    persistence_service = PersistenceService(
        repository=repository,
        cache=cache,
        cache_ttl_seconds=settings.cache_ttl_seconds,
        lock_ttl_seconds=settings.lock_ttl_seconds,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await mongo_client.close()
        await cache.close()

    app = FastAPI(title="pdf-extractext-persistence-svc", lifespan=lifespan)
    app.state.settings = settings
    app.state.mongo_client = mongo_client
    app.state.persistence_service = persistence_service
    app.include_router(api_v1_router)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
    return app


async def _unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    error = ErrorResponse(error_code=INTERNAL_ERROR_CODE, message=INTERNAL_ERROR_MESSAGE)
    return JSONResponse(status_code=500, content=error.model_dump())


settings = Settings()
app = create_app(settings)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
