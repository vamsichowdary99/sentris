import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import AlertStatus, Severity
from app.schemas.common import ORMModel


class AlertSearchFilters(BaseModel):
    """Structured, allow-listed alert filters — shared by GET /alerts and
    POST /search. This is the safe filter shape a future NL-search layer
    (Phase 6) will translate free text into; it never accepts raw SQL."""

    status: AlertStatus | None = None
    severity: Severity | None = None
    source: str | None = None
    src_ip: str | None = None
    q: str | None = None
    mitre: str | None = None
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None


class SavedSearchCreate(BaseModel):
    name: str
    query: dict[str, Any]


class SavedSearchRead(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    query: dict[str, Any]
    created_at: datetime
    updated_at: datetime
