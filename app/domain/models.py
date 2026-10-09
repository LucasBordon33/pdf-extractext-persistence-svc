from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PDFDocument(BaseModel):
    id: str | None = None
    name: str
    checksum: str
    content: str
    size: int = 0
    created_at: datetime | None = None

    def _excluded_fields(self) -> set[str] | None:
        return {"id"} if self.id is None else None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude=self._excluded_fields())

    def to_json(self) -> str:
        return self.model_dump_json(exclude=self._excluded_fields())
