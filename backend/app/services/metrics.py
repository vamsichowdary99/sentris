from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.metrics import MetricsRepository
from app.schemas.metrics import AnalystMetrics, MetricsOverview, MitreHeatmapEntry, MTTRMetrics


class MetricsService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = MetricsRepository(session)

    async def overview(self, org_id: uuid.UUID) -> MetricsOverview:
        return MetricsOverview(
            total_alerts=await self.repo.total_alerts(org_id),
            total_cases=await self.repo.total_cases(org_id),
            open_cases=await self.repo.open_cases(org_id),
            alerts_by_status=await self.repo.alerts_by_status(org_id),
            alerts_by_severity=await self.repo.alerts_by_severity(org_id),
            cases_by_status=await self.repo.cases_by_status(org_id),
        )

    async def mttr(self, org_id: uuid.UUID) -> MTTRMetrics:
        average_hours, sample_size = await self.repo.mttr_hours(org_id)
        return MTTRMetrics(average_hours=average_hours, sample_size=sample_size)

    async def mitre_heatmap(self, org_id: uuid.UUID) -> list[MitreHeatmapEntry]:
        rows = await self.repo.mitre_heatmap(org_id)
        return [
            MitreHeatmapEntry(
                technique_id=tid, technique_name=name, tactic=tactic, alert_count=count
            )
            for tid, name, tactic, count in rows
        ]

    async def analyst_workload(self, org_id: uuid.UUID) -> list[AnalystMetrics]:
        rows = await self.repo.analyst_workload(org_id)
        return [
            AnalystMetrics(
                analyst_id=uid, full_name=name, assigned_cases=total, closed_cases=closed
            )
            for uid, name, total, closed in rows
        ]
