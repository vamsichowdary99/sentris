from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.saved_search import SavedSearch
from app.repositories.alert import AlertRepository
from app.repositories.saved_search import SavedSearchRepository
from app.schemas.search import AlertSearchFilters, SavedSearchCreate


class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.alert_repo = AlertRepository(session)
        self.saved_repo = SavedSearchRepository(session)

    async def search_alerts(
        self, org_id: uuid.UUID, filters: AlertSearchFilters, offset: int, limit: int
    ) -> tuple[list[Alert], int]:
        return await self.alert_repo.list_page(
            org_id,
            offset,
            limit,
            status=filters.status,
            severity=filters.severity,
            source=filters.source,
            src_ip=filters.src_ip,
            q=filters.q,
            mitre=filters.mitre,
            occurred_from=filters.occurred_from,
            occurred_to=filters.occurred_to,
        )

    async def save(self, user_id: uuid.UUID, data: SavedSearchCreate) -> SavedSearch:
        saved = await self.saved_repo.create(user_id, data.name, data.query)
        await self.session.commit()
        return saved

    async def list_saved(self, user_id: uuid.UUID) -> list[SavedSearch]:
        return await self.saved_repo.list(user_id)
