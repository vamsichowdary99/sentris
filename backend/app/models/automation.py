from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPKMixin
from app.models.enums import AutomationStatus


class AutomationRun(Base, UUIDPKMixin):
    """Playbook execution record (Phase 7 SOAR-lite)."""

    __tablename__ = "automation_runs"

    trigger: Mapped[str] = mapped_column(String(100), nullable=False)
    playbook: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[AutomationStatus] = mapped_column(
        Enum(AutomationStatus, name="automation_status"),
        nullable=False,
        default=AutomationStatus.pending,
    )
    steps: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
