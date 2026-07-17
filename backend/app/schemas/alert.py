import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, IPvAnyAddress

from app.models.enums import AlertStatus, MitreMappingSource, Severity
from app.schemas.ai_analysis import AIAnalysisRead
from app.schemas.common import ORMModel
from app.schemas.ioc import IOCDetail
from app.schemas.mitre import MitreTechniqueRead


class AlertCreate(BaseModel):
    source: str
    external_id: str | None = None
    title: str
    raw: dict[str, Any]
    severity: Severity = Severity.medium
    rule_name: str | None = None
    src_ip: IPvAnyAddress | None = None
    dst_ip: IPvAnyAddress | None = None
    host_asset_id: uuid.UUID | None = None
    user_subject: str | None = None
    occurred_at: datetime


class AlertUpdate(BaseModel):
    status: AlertStatus | None = None
    severity: Severity | None = None
    host_asset_id: uuid.UUID | None = None


class AlertRead(ORMModel):
    id: uuid.UUID
    org_id: uuid.UUID
    source: str
    external_id: str | None
    title: str
    severity: Severity
    ai_severity: Severity | None
    priority: int | None
    status: AlertStatus
    rule_name: str | None
    src_ip: IPvAnyAddress | None
    dst_ip: IPvAnyAddress | None
    host_asset_id: uuid.UUID | None
    user_subject: str | None
    occurred_at: datetime
    ingested_at: datetime
    created_at: datetime
    updated_at: datetime


class AlertMitreMappingRead(BaseModel):
    technique: MitreTechniqueRead
    source: MitreMappingSource
    confidence: float | None


class AlertEventRead(ORMModel):
    id: uuid.UUID
    alert_id: uuid.UUID
    event_ts: datetime
    payload: dict[str, Any]


class AlertDetail(AlertRead):
    raw: dict[str, Any]
    iocs: list[IOCDetail] = []
    mitre: list[AlertMitreMappingRead] = []
    ai_analyses: list[AIAnalysisRead] = []
