from fastapi import APIRouter

from app.db.connection import mongodb

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check():
    db_healthy = await mongodb.ping()
    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": "squad-nous",
        "database": "connected" if db_healthy else "disconnected",
    }
