from __future__ import annotations

import uuid

from sqlalchemy import case as sql_case
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.case import Case
from app.models.mitre import AlertMitreTechnique, MitreTechnique
from app.models.user import User


class MetricsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def total_alerts(self, org_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Alert).where(Alert.org_id == org_id)
        return (await self.session.execute(stmt)).scalar_one()

    async def alerts_by_status(self, org_id: uuid.UUID) -> dict[str, int]:
        stmt = (
            select(Alert.status, func.count())
            .where(Alert.org_id == org_id)
            .group_by(Alert.status)
        )
        rows = (await self.session.execute(stmt)).all()
        return {status.value: count for status, count in rows}

    async def alerts_by_severity(self, org_id: uuid.UUID) -> dict[str, int]:
        stmt = (
            select(Alert.severity, func.count())
            .where(Alert.org_id == org_id)
            .group_by(Alert.severity)
        )
        rows = (await self.session.execute(stmt)).all()
        return {severity.value: count for severity, count in rows}

    async def total_cases(self, org_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Case).where(Case.org_id == org_id)
        return (await self.session.execute(stmt)).scalar_one()

    async def open_cases(self, org_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Case)
            .where(Case.org_id == org_id, Case.status != "closed")
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def cases_by_status(self, org_id: uuid.UUID) -> dict[str, int]:
        stmt = (
            select(Case.status, func.count()).where(Case.org_id == org_id).group_by(Case.status)
        )
        rows = (await self.session.execute(stmt)).all()
        return {status.value: count for status, count in rows}

    async def mttr_hours(self, org_id: uuid.UUID) -> tuple[float | None, int]:
        duration_hours = func.extract("epoch", Case.closed_at - Case.opened_at) / 3600.0
        stmt = select(func.avg(duration_hours), func.count()).where(
            Case.org_id == org_id, Case.closed_at.is_not(None)
        )
        avg_hours, sample_size = (await self.session.execute(stmt)).one()
        return (float(avg_hours) if avg_hours is not None else None, sample_size)

    async def mitre_heatmap(self, org_id: uuid.UUID) -> list[tuple[str, str, str, int]]:
        stmt = (
            select(
                MitreTechnique.id,
                MitreTechnique.name,
                MitreTechnique.tactic,
                func.count(AlertMitreTechnique.alert_id),
            )
            .join(AlertMitreTechnique, AlertMitreTechnique.technique_id == MitreTechnique.id)
            .join(Alert, Alert.id == AlertMitreTechnique.alert_id)
            .where(Alert.org_id == org_id)
            .group_by(MitreTechnique.id, MitreTechnique.name, MitreTechnique.tactic)
            .order_by(func.count(AlertMitreTechnique.alert_id).desc())
        )
        return list((await self.session.execute(stmt)).tuples().all())

    async def analyst_workload(self, org_id: uuid.UUID) -> list[tuple[str, str, int, int]]:
        closed_count = func.sum(sql_case((Case.status == "closed", 1), else_=0))
        stmt = (
            select(User.id, User.full_name, func.count(Case.id), closed_count)
            .join(Case, Case.assignee_id == User.id)
            .where(Case.org_id == org_id)
            .group_by(User.id, User.full_name)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(str(uid), name, total, int(closed)) for uid, name, total, closed in rows]
