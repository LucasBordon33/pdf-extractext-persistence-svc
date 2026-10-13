from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from app.api.deps import get_persistence_service
from app.api.v1.schemas import DocumentResponse, ErrorResponse, StoreRequest, StoreResponse
from app.domain.services.persistence_service import PersistenceService

NOT_FOUND_MESSAGE = "No document found for the given checksum"

router = APIRouter()

PersistenceServiceDep = Annotated[PersistenceService, Depends(get_persistence_service)]


@router.post("/store", status_code=201, response_model=StoreResponse)
async def store_document(payload: StoreRequest, service: PersistenceServiceDep) -> StoreResponse:
    result = await service.store(
        name=payload.name, text=payload.text, checksum=payload.checksum, size=payload.size
    )
    if result.get("status") == 409:
        return _error_response(409, "DUPLICATE_DOCUMENT", result["detail"])
    return StoreResponse(id=result["id"], checksum=result["checksum"])


@router.get("/documents/{checksum}", response_model=DocumentResponse)
async def get_document(checksum: str, service: PersistenceServiceDep) -> DocumentResponse:
    document = await service.fetch(checksum)
    if document is None:
        return _error_response(404, "DOCUMENT_NOT_FOUND", NOT_FOUND_MESSAGE)
    return DocumentResponse(**document)


@router.delete("/documents/{checksum}", status_code=204)
async def delete_document(checksum: str, service: PersistenceServiceDep) -> Response:
    deleted = await service.delete(checksum)
    if not deleted:
        return _error_response(404, "DOCUMENT_NOT_FOUND", NOT_FOUND_MESSAGE)
    return Response(status_code=204)


def _error_response(status_code: int, error_code: str, message: str) -> JSONResponse:
    error = ErrorResponse(error_code=error_code, message=message)
    return JSONResponse(status_code=status_code, content=error.model_dump())
