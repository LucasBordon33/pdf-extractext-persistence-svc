from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.adapters.mongo.client import MongoClient
from app.api.deps import get_mongo_client
from app.api.v1.schemas import HealthResponse

VERSION = "1.0.0"

router = APIRouter()

MongoClientDep = Annotated[MongoClient | None, Depends(get_mongo_client)]


@router.get("/health", response_model=HealthResponse)
async def health(mongo_client: MongoClientDep) -> JSONResponse:
    if mongo_client is None:
        status = "ok"
    else:
        status = await _mongo_health_status(mongo_client)

    body = HealthResponse(status=status, version=VERSION).model_dump()
    return JSONResponse(status_code=200 if status == "ok" else 503, content=body)


async def _mongo_health_status(mongo_client: MongoClient) -> str:
    try:
        reachable = await mongo_client.ping()
    except Exception:  # noqa: BLE001
        reachable = False
    return "ok" if reachable else "degraded"
