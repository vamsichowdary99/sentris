from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.asset import Asset
from app.repositories.asset import AssetRepository
from app.schemas.asset import AssetCreate, AssetUpdate


class AssetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AssetRepository(session)

    async def create(self, org_id: uuid.UUID, data: AssetCreate) -> Asset:
        fields = data.model_dump()
        if fields.get("ip") is not None:
            fields["ip"] = str(fields["ip"])
        asset = await self.repo.create(org_id, **fields)
        await self.session.commit()
        return asset

    async def get(self, org_id: uuid.UUID, asset_id: uuid.UUID) -> Asset:
        asset = await self.repo.get(org_id, asset_id)
        if asset is None:
            raise NotFoundError(f"Asset {asset_id} not found")
        return asset

    async def list_page(
        self, org_id: uuid.UUID, offset: int, limit: int
    ) -> tuple[list[Asset], int]:
        return await self.repo.list_page(org_id, offset, limit)

    async def update(self, org_id: uuid.UUID, asset_id: uuid.UUID, data: AssetUpdate) -> Asset:
        asset = await self.get(org_id, asset_id)
        fields = data.model_dump(exclude_unset=True)
        if fields.get("ip") is not None:
            fields["ip"] = str(fields["ip"])
        asset = await self.repo.update(asset, **fields)
        await self.session.commit()
        return asset
