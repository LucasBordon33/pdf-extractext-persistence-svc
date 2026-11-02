from datetime import datetime

from pydantic import BaseModel


class StoreRequest(BaseModel):
    name: str
    text: str
    checksum: str
    size: int = 0


class StoreResponse(BaseModel):
    id: str
    checksum: str


class DocumentResponse(BaseModel):
    id: str
    name: str
    checksum: str
    content: str
    size: int
    created_at: datetime | None


class UpdateDocumentRequest(BaseModel):
    name: str | None = None
    text: str | None = None
    size: int | None = None


class ErrorResponse(BaseModel):
    error_code: str
    message: str


class HealthResponse(BaseModel):
    status: str
    version: str
