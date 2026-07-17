from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ReportFormat
from app.models.report import Report


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, case_id: uuid.UUID, format: ReportFormat, content: str, generated_by: uuid.UUID
    ) -> Report:
        report = Report(case_id=case_id, format=format, content=content, generated_by=generated_by)
        self.session.add(report)
        await self.session.flush()
        return report

    async def list_for_case(self, case_id: uuid.UUID) -> list[Report]:
        stmt = (
            select(Report).where(Report.case_id == case_id).order_by(Report.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())
