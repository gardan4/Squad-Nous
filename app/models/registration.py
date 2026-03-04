from typing import Any

from pydantic import BaseModel


class HistoryEntry(BaseModel):
    fields: dict[str, Any]
    schema_version: str
    archived_at: str


class Registration(BaseModel):
    pii_hash: str
    fields: dict[str, Any]
    schema_version: str
    history: list[HistoryEntry] = []
    created_at: str
    updated_at: str
