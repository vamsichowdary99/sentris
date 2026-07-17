import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class UserRead(ORMModel):
    id: uuid.UUID
    org_id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


class UserMe(BaseModel):
    user: UserRead
    roles: list[str]
    permissions: list[str]
