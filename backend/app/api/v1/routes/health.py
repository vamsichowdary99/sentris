import redis.asyncio as redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Liveness probe — no dependencies, just confirms the process is up."""
    return {"status": "ok", "app": get_settings().app_name}


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db_session)) -> dict:
    """Readiness probe — confirms Postgres and Redis are reachable."""
    settings = get_settings()
    checks = {"database": "unknown", "redis": "unknown"}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 - surfaced in response, not swallowed
        checks["database"] = f"error: {exc}"

    try:
        client = redis.from_url(settings.redis_url)
        await client.ping()
        await client.aclose()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc}"

    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, **checks}
