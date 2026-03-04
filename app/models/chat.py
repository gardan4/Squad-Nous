from typing import Any

from pydantic import BaseModel, Field


class CreateSessionResponse(BaseModel):
    session_id: str
    status: str


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1, max_length=5000)


class ChatResponse(BaseModel):
    session_id: str
    response: str
    status: str
    extracted_fields: dict[str, Any] = {}


class SessionResponse(BaseModel):
    session_id: str
    status: str
    messages: list[dict[str, Any]] = []
    extracted_fields: dict[str, Any] = {}
    schema_version: str
    created_at: str
