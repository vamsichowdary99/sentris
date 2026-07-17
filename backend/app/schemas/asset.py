import uuid
from datetime import datetime

from pydantic import BaseModel, IPvAnyAddress

from app.models.enums import AssetCriticality
from app.schemas.common import ORMModel


class AssetCreate(BaseModel):
    hostname: str
    ip: IPvAnyAddress | None = None
    os: str | None = None
    owner: str | None = None
    criticality: AssetCriticality = AssetCriticality.medium
    tags: list[str] | None = None


class AssetUpdate(BaseModel):
    hostname: str | None = None
    ip: IPvAnyAddress | None = None
    os: str | None = None
    owner: str | None = None
    criticality: AssetCriticality | None = None
    tags: list[str] | None = None


class AssetRead(ORMModel):
    id: uuid.UUID
    org_id: uuid.UUID
    hostname: str
    ip: IPvAnyAddress | None
    os: str | None
    owner: str | None
    criticality: AssetCriticality
    tags: list[str] | None
    created_at: datetime
    updated_at: datetime
