from abc import ABC, abstractmethod

from app.domain.models import PDFDocument


class DocumentRepository(ABC):
    @abstractmethod
    async def save(self, doc: PDFDocument) -> str:
        ...

    @abstractmethod
    async def find_by_checksum(self, checksum: str) -> PDFDocument | None:
        ...

    @abstractmethod
    async def find_by_id(self, doc_id: str) -> PDFDocument | None:
        ...

    @abstractmethod
    async def delete(self, doc_id: str) -> bool:
        ...

    @abstractmethod
    async def find_all(self) -> list[PDFDocument]:
        ...
