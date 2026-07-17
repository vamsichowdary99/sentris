import uuid
from datetime import datetime
from typing import Any

from app.models.enums import AITask
from app.schemas.common import ORMModel


class AIAnalysisRead(ORMModel):
    id: uuid.UUID
    task: AITask
    model: str
    provider: str
    prompt_version: str
    output: dict[str, Any]
    created_at: datetime
