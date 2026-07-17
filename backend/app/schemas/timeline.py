import uuid
from datetime import datetime
from typing import Any

from app.schemas.common import ORMModel


class TimelineEventRead(ORMModel):
    id: uuid.UUID
    case_id: uuid.UUID
    ts: datetime
    kind: str
    actor_id: uuid.UUID | None
    description: str
    meta: dict[str, Any] | None
