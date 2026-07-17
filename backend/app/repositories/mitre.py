from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mitre import AlertMitreTechnique, MitreTechnique


class MitreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, technique_id: str) -> MitreTechnique | None:
        return await self.session.get(MitreTechnique, technique_id)

    async def list_page(
        self, offset: int, limit: int, tactic: str | None = None
    ) -> tuple[list[MitreTechnique], int]:
        base = select(MitreTechnique)
        if tactic:
            base = base.where(MitreTechnique.tactic == tactic)
        total = (
            await self.session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = base.order_by(MitreTechnique.id).offset(offset).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()
        return list(items), total

    async def list_for_alert(
        self, alert_id: uuid.UUID
    ) -> list[tuple[MitreTechnique, AlertMitreTechnique]]:
        stmt = (
            select(MitreTechnique, AlertMitreTechnique)
            .join(
                AlertMitreTechnique,
                AlertMitreTechnique.technique_id == MitreTechnique.id,
            )
            .where(AlertMitreTechnique.alert_id == alert_id)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows]

    async def map_alert(
        self,
        alert_id: uuid.UUID,
        technique_id: str,
        source: str,
        confidence: float | None = None,
    ) -> AlertMitreTechnique:
        mapping = AlertMitreTechnique(
            alert_id=alert_id, technique_id=technique_id, source=source, confidence=confidence
        )
        self.session.add(mapping)
        await self.session.flush()
        return mapping

    async def upsert_mapping(
        self,
        alert_id: uuid.UUID,
        technique_id: str,
        source: str,
        confidence: float | None = None,
    ) -> AlertMitreTechnique:
        """Like map_alert, but safe to call when the same alert+technique may
        already be mapped (e.g. the AI mapper suggesting a technique the
        rule-based mapper already caught) — updates source/confidence
        instead of violating the composite PK."""
        stmt = (
            pg_insert(AlertMitreTechnique)
            .values(
                alert_id=alert_id, technique_id=technique_id, source=source, confidence=confidence
            )
            .on_conflict_do_update(
                index_elements=[AlertMitreTechnique.alert_id, AlertMitreTechnique.technique_id],
                set_={"source": source, "confidence": confidence},
            )
            .returning(AlertMitreTechnique)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()
