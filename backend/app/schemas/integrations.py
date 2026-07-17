from typing import Literal

from pydantic import BaseModel

from app.models.enums import IOCType


class IntegrationStatusRead(BaseModel):
    provider: str
    mode: Literal["live", "mocked"]
    configured: bool
    last_status: str | None
    supported_types: list[IOCType]
