from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


@asynccontextmanager
async def worker_session() -> AsyncIterator[AsyncSession]:
    """A DB session for use inside a Celery task.

    Each task call runs its own `asyncio.run()` loop (see
    `app.workers.tasks`), so it needs a connection pool it fully owns rather
    than the api process's module-level engine — reusing pooled asyncpg
    connections across separate event loops raises "attached to a different
    loop". NullPool means every checkout opens a fresh connection under the
    task's own loop and nothing outlives it.
    """
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()
