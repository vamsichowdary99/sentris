from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.ioc import IOC, Enrichment
from app.repositories.ioc import IOCRepository
from app.schemas.ioc import IOCCreate


class IOCService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = IOCRepository(session)

    async def create(self, org_id: uuid.UUID, data: IOCCreate) -> IOC:
        ioc = await self.repo.get_or_create(
            org_id,
            type=data.type,
            value=data.value,
            reputation=data.reputation,
            source=data.source,
        )
        await self.session.commit()
        return ioc

    async def get(self, org_id: uuid.UUID, ioc_id: uuid.UUID) -> IOC:
        ioc = await self.repo.get(org_id, ioc_id)
        if ioc is None:
            raise NotFoundError(f"IOC {ioc_id} not found")
        return ioc

    async def get_enrichments(self, ioc_id: uuid.UUID) -> list[Enrichment]:
        return await self.repo.list_enrichments(ioc_id)

    async def list_page(self, org_id: uuid.UUID, offset: int, limit: int) -> tuple[list[IOC], int]:
        return await self.repo.list_page(org_id, offset, limit)
