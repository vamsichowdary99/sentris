from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        org_id: uuid.UUID,
        action: str,
        entity_type: str,
        user_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> AuditLog:
        log = AuditLog(
            org_id=org_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip=ip,
            user_agent=user_agent,
            meta=meta,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def list_page(
        self, org_id: uuid.UUID, offset: int, limit: int
    ) -> tuple[list[AuditLog], int]:
        base = select(AuditLog).where(AuditLog.org_id == org_id)
        total = (
            await self.session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = base.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()
        return list(items), total
