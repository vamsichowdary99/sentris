from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.case import Case, CaseAlert
from app.models.ioc import IOC, AlertIOC, Enrichment


class IOCRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(
        self, org_id: uuid.UUID, type: str, value: str, **fields: object
    ) -> IOC:
        stmt = select(IOC).where(IOC.org_id == org_id, IOC.value == value)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return existing

        ioc = IOC(org_id=org_id, type=type, value=value, **fields)
        self.session.add(ioc)
        await self.session.flush()
        return ioc

    async def get(self, org_id: uuid.UUID, ioc_id: uuid.UUID) -> IOC | None:
        stmt = select(IOC).where(IOC.org_id == org_id, IOC.id == ioc_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_page(
        self, org_id: uuid.UUID, offset: int, limit: int
    ) -> tuple[list[IOC], int]:
        base = select(IOC).where(IOC.org_id == org_id)
        total = (
            await self.session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = base.order_by(IOC.created_at.desc()).offset(offset).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()
        return list(items), total

    async def link_to_alert(self, alert_id: uuid.UUID, ioc_id: uuid.UUID) -> None:
        stmt = (
            pg_insert(AlertIOC)
            .values(alert_id=alert_id, ioc_id=ioc_id)
            .on_conflict_do_nothing()
        )
        await self.session.execute(stmt)

    async def list_for_alert(self, alert_id: uuid.UUID) -> list[IOC]:
        stmt = (
            select(IOC).join(AlertIOC, AlertIOC.ioc_id == IOC.id).where(
                AlertIOC.alert_id == alert_id
            )
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_enrichments(self, ioc_id: uuid.UUID) -> list[Enrichment]:
        stmt = select(Enrichment).where(Enrichment.ioc_id == ioc_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def upsert_enrichment(
        self,
        ioc_id: uuid.UUID,
        provider: str,
        verdict: str | None,
        score: float | None,
        raw: dict[str, Any],
        fetched_at: datetime,
    ) -> Enrichment:
        stmt = (
            pg_insert(Enrichment)
            .values(
                ioc_id=ioc_id,
                provider=provider,
                verdict=verdict,
                score=score,
                raw=raw,
                fetched_at=fetched_at,
            )
            .on_conflict_do_update(
                index_elements=[Enrichment.ioc_id, Enrichment.provider],
                set_={"verdict": verdict, "score": score, "raw": raw, "fetched_at": fetched_at},
            )
            .returning(Enrichment)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()

    async def update_reputation(self, ioc: IOC, reputation: str, seen_at: datetime) -> None:
        ioc.reputation = reputation
        if ioc.first_seen is None:
            ioc.first_seen = seen_at
        ioc.last_seen = seen_at
        await self.session.flush()

    async def list_alerts_for_ioc(self, ioc_id: uuid.UUID) -> list[Alert]:
        """The reverse of list_for_alert — every alert this indicator was
        seen on, so an analyst can pivot from Investigate straight to the
        alerts that triggered it."""
        stmt = (
            select(Alert)
            .join(AlertIOC, AlertIOC.alert_id == Alert.id)
            .where(AlertIOC.ioc_id == ioc_id)
            .order_by(Alert.occurred_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_cases_for_ioc(self, ioc_id: uuid.UUID) -> list[Case]:
        stmt = (
            select(Case)
            .join(CaseAlert, CaseAlert.case_id == Case.id)
            .join(AlertIOC, AlertIOC.alert_id == CaseAlert.alert_id)
            .where(AlertIOC.ioc_id == ioc_id)
            .distinct()
            .order_by(Case.opened_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())
