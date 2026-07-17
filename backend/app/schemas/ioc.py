import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import IOCType
from app.schemas.common import ORMModel


class IOCCreate(BaseModel):
    type: IOCType
    value: str
    reputation: str | None = None
    source: str | None = None


class EnrichmentRead(ORMModel):
    id: uuid.UUID
    ioc_id: uuid.UUID
    provider: str
    verdict: str | None
    score: float | None
    raw: dict[str, Any]
    fetched_at: datetime


class IOCRead(ORMModel):
    id: uuid.UUID
    org_id: uuid.UUID
    type: IOCType
    value: str
    reputation: str | None
    first_seen: datetime | None
    last_seen: datetime | None
    source: str | None
    created_at: datetime
    updated_at: datetime


class IOCDetail(IOCRead):
    enrichments: list[EnrichmentRead] = []
