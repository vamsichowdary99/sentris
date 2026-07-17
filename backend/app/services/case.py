from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.case import Case
from app.models.comment import Comment
from app.models.enums import CaseStatus
from app.repositories.audit_log import AuditLogRepository
from app.repositories.case import CaseRepository
from app.schemas.alert import AlertRead
from app.schemas.case import CaseCreate, CaseDetail, CaseRead, CaseUpdate
from app.schemas.comment import CommentRead
from app.schemas.timeline import TimelineEventRead


class CaseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CaseRepository(session)
        self.audit_repo = AuditLogRepository(session)

    async def create(self, org_id: uuid.UUID, created_by: uuid.UUID, data: CaseCreate) -> Case:
        case = await self.repo.create(
            org_id,
            title=data.title,
            summary=data.summary,
            severity=data.severity,
            created_by=created_by,
            opened_at=datetime.now(UTC),
        )
        await self.repo.add_timeline_event(
            case.id,
            kind="case_opened",
            description=f"Case opened: {case.title}",
            actor_id=created_by,
        )
        for alert_id in data.alert_ids:
            await self.repo.link_alert(case.id, alert_id)
            await self.repo.add_timeline_event(
                case.id,
                kind="alert_linked",
                description=f"Alert {alert_id} linked to case",
                actor_id=created_by,
            )
        await self.audit_repo.create(
            org_id, action="case.create", entity_type="case", user_id=created_by, entity_id=case.id
        )
        await self.session.commit()
        await self.session.refresh(case)
        return case

    async def get(self, org_id: uuid.UUID, case_id: uuid.UUID) -> Case:
        case = await self.repo.get(org_id, case_id)
        if case is None:
            raise NotFoundError(f"Case {case_id} not found")
        return case

    async def get_detail(self, org_id: uuid.UUID, case_id: uuid.UUID) -> CaseDetail:
        case = await self.get(org_id, case_id)
        alerts = await self.repo.list_alerts(case.id)
        timeline = await self.repo.list_timeline(case.id)
        comments = await self.repo.list_comments(case.id)

        return CaseDetail(
            **CaseRead.model_validate(case).model_dump(),
            alerts=[AlertRead.model_validate(a) for a in alerts],
            timeline=[TimelineEventRead.model_validate(t) for t in timeline],
            comments=[CommentRead.model_validate(c) for c in comments],
        )

    async def update(
        self, org_id: uuid.UUID, case_id: uuid.UUID, actor_id: uuid.UUID, data: CaseUpdate
    ) -> Case:
        case = await self.get(org_id, case_id)
        fields = data.model_dump(exclude_unset=True)

        new_status = fields.get("status")
        if new_status is not None and new_status != case.status:
            if new_status == CaseStatus.closed:
                fields["closed_at"] = datetime.now(UTC)
            await self.repo.add_timeline_event(
                case.id,
                kind="status_changed",
                description=f"Status changed from {case.status.value} to {new_status.value}",
                actor_id=actor_id,
            )
            await self.audit_repo.create(
                org_id,
                action="case.status_changed",
                entity_type="case",
                user_id=actor_id,
                entity_id=case.id,
                meta={"from": case.status.value, "to": new_status.value},
            )

        case = await self.repo.update(case, **fields)
        await self.session.commit()
        return case

    async def link_alerts(
        self, org_id: uuid.UUID, case_id: uuid.UUID, actor_id: uuid.UUID, alert_ids: list[uuid.UUID]
    ) -> Case:
        case = await self.get(org_id, case_id)
        for alert_id in alert_ids:
            await self.repo.link_alert(case.id, alert_id)
            await self.repo.add_timeline_event(
                case.id,
                kind="alert_linked",
                description=f"Alert {alert_id} linked to case",
                actor_id=actor_id,
            )
        await self.session.commit()
        return case

    async def add_comment(
        self, org_id: uuid.UUID, case_id: uuid.UUID, user_id: uuid.UUID, body: str
    ) -> Comment:
        case = await self.get(org_id, case_id)
        comment = await self.repo.add_comment(case.id, user_id, body)
        await self.repo.add_timeline_event(
            case.id, kind="comment_added", description="Comment added", actor_id=user_id
        )
        await self.session.commit()
        return comment

    async def list_page(
        self, org_id: uuid.UUID, offset: int, limit: int, status: CaseStatus | None = None
    ) -> tuple[list[Case], int]:
        return await self.repo.list_page(org_id, offset, limit, status=status)
