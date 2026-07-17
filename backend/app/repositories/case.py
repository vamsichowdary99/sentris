from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.case import Case, CaseAlert
from app.models.comment import Comment
from app.models.enums import CaseStatus, CommentEntityType
from app.models.timeline import TimelineEvent


class CaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, org_id: uuid.UUID, **fields: object) -> Case:
        case = Case(org_id=org_id, **fields)
        self.session.add(case)
        await self.session.flush()
        return case

    async def get(self, org_id: uuid.UUID, case_id: uuid.UUID) -> Case | None:
        stmt = select(Case).where(Case.org_id == org_id, Case.id == case_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def update(self, case: Case, **fields: object) -> Case:
        for key, value in fields.items():
            if value is not None:
                setattr(case, key, value)
        await self.session.flush()
        return case

    async def list_page(
        self,
        org_id: uuid.UUID,
        offset: int,
        limit: int,
        status: CaseStatus | None = None,
    ) -> tuple[list[Case], int]:
        base = select(Case).where(Case.org_id == org_id)
        if status is not None:
            base = base.where(Case.status == status)
        total = (
            await self.session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = base.order_by(Case.opened_at.desc()).offset(offset).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()
        return list(items), total

    async def link_alert(self, case_id: uuid.UUID, alert_id: uuid.UUID) -> None:
        stmt = (
            pg_insert(CaseAlert)
            .values(case_id=case_id, alert_id=alert_id)
            .on_conflict_do_nothing()
        )
        await self.session.execute(stmt)

    async def list_alerts(self, case_id: uuid.UUID) -> list[Alert]:
        stmt = select(Alert).join(CaseAlert, CaseAlert.alert_id == Alert.id).where(
            CaseAlert.case_id == case_id
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def add_timeline_event(
        self,
        case_id: uuid.UUID,
        kind: str,
        description: str,
        actor_id: uuid.UUID | None = None,
        meta: dict[str, Any] | None = None,
        ts: datetime | None = None,
    ) -> TimelineEvent:
        event = TimelineEvent(
            case_id=case_id,
            ts=ts or datetime.now(UTC),
            kind=kind,
            actor_id=actor_id,
            description=description,
            meta=meta,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_timeline(self, case_id: uuid.UUID) -> list[TimelineEvent]:
        stmt = select(TimelineEvent).where(TimelineEvent.case_id == case_id).order_by(
            TimelineEvent.ts
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def add_comment(
        self, case_id: uuid.UUID, user_id: uuid.UUID, body: str
    ) -> Comment:
        comment = Comment(
            entity_type=CommentEntityType.case,
            entity_id=case_id,
            user_id=user_id,
            body=body,
        )
        self.session.add(comment)
        await self.session.flush()
        return comment

    async def list_comments(self, case_id: uuid.UUID) -> list[Comment]:
        stmt = (
            select(Comment)
            .where(
                Comment.entity_type == CommentEntityType.case,
                Comment.entity_id == case_id,
            )
            .order_by(Comment.created_at)
        )
        return list((await self.session.execute(stmt)).scalars().all())
