from fastapi import APIRouter

from app.db.connection import mongodb

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/sessions")
async def list_sessions(limit: int = 50, status: str | None = None):
    """List all sessions with their messages and extracted fields."""
    query = {}
    if status:
        query["status"] = status
    cursor = mongodb.db["sessions"].find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    sessions = await cursor.to_list(length=limit)
    # Convert datetimes to strings
    for s in sessions:
        for key in ("created_at", "updated_at"):
            if hasattr(s.get(key), "isoformat"):
                s[key] = s[key].isoformat()
    return {"sessions": sessions, "count": len(sessions)}


@router.get("/registrations")
async def list_registrations(limit: int = 50):
    """List all completed registrations with history."""
    cursor = mongodb.db["registrations"].find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    registrations = await cursor.to_list(length=limit)
    for r in registrations:
        for key in ("created_at", "updated_at"):
            if hasattr(r.get(key), "isoformat"):
                r[key] = r[key].isoformat()
    return {"registrations": registrations, "count": len(registrations)}


@router.get("/stats")
async def get_stats():
    """Get overview statistics."""
    sessions_count = await mongodb.db["sessions"].count_documents({})
    active_count = await mongodb.db["sessions"].count_documents({"status": "active"})
    completed_count = await mongodb.db["sessions"].count_documents({"status": "completed"})
    registrations_count = await mongodb.db["registrations"].count_documents({})
    return {
        "sessions": {
            "total": sessions_count,
            "active": active_count,
            "completed": completed_count,
        },
        "registrations": registrations_count,
    }


@router.delete("/sessions")
async def clear_sessions():
    """Delete all sessions (for development)."""
    result = await mongodb.db["sessions"].delete_many({})
    return {"deleted": result.deleted_count}


@router.delete("/registrations")
async def clear_registrations():
    """Delete all registrations (for development)."""
    result = await mongodb.db["registrations"].delete_many({})
    return {"deleted": result.deleted_count}
