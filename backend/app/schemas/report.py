import uuid
from datetime import datetime

from app.models.enums import ReportFormat
from app.schemas.common import ORMModel


class ReportRead(ORMModel):
    id: uuid.UUID
    case_id: uuid.UUID
    format: ReportFormat
    content: str
    generated_by: uuid.UUID
    created_at: datetime
