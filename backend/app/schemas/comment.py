import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import CommentEntityType
from app.schemas.common import ORMModel


class CommentCreate(BaseModel):
    body: str


class CommentRead(ORMModel):
    id: uuid.UUID
    entity_type: CommentEntityType
    entity_id: uuid.UUID
    user_id: uuid.UUID
    body: str
    created_at: datetime
