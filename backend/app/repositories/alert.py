from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertEvent
from app.models.enums import AlertStatus, Severity
from app.models.mitre import AlertMitreTechnique


class AlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, org_id: uuid.UUID, **fields: object) -> Alert:
        alert = Alert(org_id=org_id, **fields)
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def get(self, org_id: uuid.UUID, alert_id: uuid.UUID) -> Alert | None:
        stmt = select(Alert).where(Alert.org_id == org_id, Alert.id == alert_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def update(self, alert: Alert, **fields: object) -> Alert:
        for key, value in fields.items():
            if value is not None:
                setattr(alert, key, value)
        await self.session.flush()
        return alert

    async def list_page(
        self,
        org_id: uuid.UUID,
        offset: int,
        limit: int,
        status: AlertStatus | None = None,
        severity: Severity | None = None,
        source: str | None = None,
        src_ip: str | None = None,
        q: str | None = None,
        mitre: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> tuple[list[Alert], int]:
        base = select(Alert).where(Alert.org_id == org_id)

        if status is not None:
            base = base.where(Alert.status == status)
        if severity is not None:
            base = base.where(Alert.severity == severity)
        if source is not None:
            base = base.where(Alert.source == source)
        if src_ip is not None:
            base = base.where(Alert.src_ip == src_ip)
        if occurred_from is not None:
            base = base.where(Alert.occurred_at >= occurred_from)
        if occurred_to is not None:
            base = base.where(Alert.occurred_at <= occurred_to)
        if q is not None:
            base = base.where(
                Alert.search_vector.op("@@")(func.plainto_tsquery("english", q))
            )
        if mitre is not None:
            base = base.where(
                Alert.id.in_(
                    select(AlertMitreTechnique.alert_id).where(
                        AlertMitreTechnique.technique_id == mitre
                    )
                )
            )

        total = (
            await self.session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = base.order_by(Alert.occurred_at.desc()).offset(offset).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()
        return list(items), total

    async def list_events(self, alert_id: uuid.UUID) -> list[AlertEvent]:
        stmt = select(AlertEvent).where(AlertEvent.alert_id == alert_id).order_by(
            AlertEvent.event_ts
        )
        return list((await self.session.execute(stmt)).scalars().all())
