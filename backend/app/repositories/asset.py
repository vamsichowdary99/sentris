from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset


class AssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, org_id: uuid.UUID, **fields: object) -> Asset:
        asset = Asset(org_id=org_id, **fields)
        self.session.add(asset)
        await self.session.flush()
        return asset

    async def get(self, org_id: uuid.UUID, asset_id: uuid.UUID) -> Asset | None:
        stmt = select(Asset).where(Asset.org_id == org_id, Asset.id == asset_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_page(
        self, org_id: uuid.UUID, offset: int, limit: int
    ) -> tuple[list[Asset], int]:
        base = select(Asset).where(Asset.org_id == org_id)
        total = (
            await self.session.execute(
                select(func.count()).select_from(base.subquery())
            )
        ).scalar_one()
        stmt = base.order_by(Asset.created_at.desc()).offset(offset).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()
        return list(items), total

    async def update(self, asset: Asset, **fields: object) -> Asset:
        for key, value in fields.items():
            if value is not None:
                setattr(asset, key, value)
        await self.session.flush()
        return asset
