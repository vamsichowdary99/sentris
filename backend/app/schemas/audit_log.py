import uuid
from datetime import datetime
from typing import Any

from pydantic import IPvAnyAddress

from app.schemas.common import ORMModel


class AuditLogRead(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    ip: IPvAnyAddress | None
    user_agent: str | None
    meta: dict[str, Any] | None
    created_at: datetime
