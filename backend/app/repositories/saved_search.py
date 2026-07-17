from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.saved_search import SavedSearch


class SavedSearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user_id: uuid.UUID, name: str, query: dict[str, Any]) -> SavedSearch:
        saved = SavedSearch(user_id=user_id, name=name, query=query)
        self.session.add(saved)
        await self.session.flush()
        return saved

    async def list(self, user_id: uuid.UUID) -> list[SavedSearch]:
        stmt = select(SavedSearch).where(SavedSearch.user_id == user_id).order_by(
            SavedSearch.created_at.desc()
        )
        return list((await self.session.execute(stmt)).scalars().all())
