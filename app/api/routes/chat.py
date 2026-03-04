from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_conversation_service
from app.models.chat import (
    ChatRequest,
    ChatResponse,
    CreateSessionResponse,
    SessionResponse,
)
from app.services.conversation import ConversationService

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/session", response_model=CreateSessionResponse)
async def create_session(
    service: ConversationService = Depends(get_conversation_service),
):
    result = await service.create_session()
    return CreateSessionResponse(**result)


@router.post("/chat", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    service: ConversationService = Depends(get_conversation_service),
):
    try:
        result = await service.process_message(request.session_id, request.message)
        return ChatResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    service: ConversationService = Depends(get_conversation_service),
):
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(
        session_id=session["session_id"],
        status=session["status"],
        messages=session.get("messages", []),
        extracted_fields=session.get("extracted_fields", {}),
        schema_version=session["schema_version"],
        created_at=session["created_at"].isoformat()
        if hasattr(session["created_at"], "isoformat")
        else str(session["created_at"]),
    )


@router.delete("/session/{session_id}")
async def close_session(
    session_id: str,
    service: ConversationService = Depends(get_conversation_service),
):
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await service.close_session(session_id)
    return {"status": "closed", "session_id": session_id}
