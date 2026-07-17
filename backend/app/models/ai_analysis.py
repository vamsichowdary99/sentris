import uuid
from typing import Any

from sqlalchemy import Enum, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import AIEntityType, AITask


class AIAnalysis(Base, UUIDPKMixin, TimestampMixin):
    """Stored output of every AI task, for reproducibility and eval (Phase 6)."""

    __tablename__ = "ai_analyses"

    entity_type: Mapped[AIEntityType] = mapped_column(
        Enum(AIEntityType, name="ai_entity_type"), nullable=False
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    task: Mapped[AITask] = mapped_column(Enum(AITask, name="ai_task"), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    output: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
