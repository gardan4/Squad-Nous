from fastapi import HTTPException


class SessionNotFoundError(HTTPException):
    def __init__(self, session_id: str):
        super().__init__(status_code=404, detail=f"Session {session_id} not found")


class SessionCompletedError(HTTPException):
    def __init__(self, session_id: str):
        super().__init__(status_code=400, detail=f"Session {session_id} is already completed")


class LLMProviderError(HTTPException):
    def __init__(self, detail: str = "LLM provider error"):
        super().__init__(status_code=502, detail=detail)
