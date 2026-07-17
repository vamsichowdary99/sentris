import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import CaseStatus, Severity
from app.schemas.alert import AlertRead
from app.schemas.comment import CommentRead
from app.schemas.common import ORMModel
from app.schemas.timeline import TimelineEventRead


class CaseCreate(BaseModel):
    title: str
    summary: str | None = None
    severity: Severity = Severity.medium
    alert_ids: list[uuid.UUID] = []


class CaseUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    status: CaseStatus | None = None
    severity: Severity | None = None
    assignee_id: uuid.UUID | None = None


class CaseRead(ORMModel):
    id: uuid.UUID
    org_id: uuid.UUID
    title: str
    summary: str | None
    status: CaseStatus
    severity: Severity
    assignee_id: uuid.UUID | None
    created_by: uuid.UUID
    opened_at: datetime
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CaseDetail(CaseRead):
    alerts: list[AlertRead] = []
    timeline: list[TimelineEventRead] = []
    comments: list[CommentRead] = []


class LinkAlertsRequest(BaseModel):
    alert_ids: list[uuid.UUID]
