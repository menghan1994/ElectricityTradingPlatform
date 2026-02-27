from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import async_session_factory

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    db_status = "healthy"
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    return {
        "status": "ok",
        "database": db_status,
    }
