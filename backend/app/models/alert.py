import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import INET, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import AlertStatus, Severity


class Alert(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "alerts"
    __table_args__ = (
        Index(
            "ix_alerts_org_status_severity_occurred",
            "org_id", "status", "severity", "occurred_at",
        ),
        Index("ix_alerts_search_vector", "search_vector", postgresql_using="gin"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="alert_severity"), nullable=False, default=Severity.medium
    )
    ai_severity: Mapped[Severity | None] = mapped_column(
        Enum(Severity, name="alert_ai_severity"), nullable=True
    )
    priority: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, name="alert_status"), nullable=False, default=AlertStatus.new
    )
    rule_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    src_ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    dst_ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    host_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    user_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    # NOTE: `embedding vector(N)` (pgvector) is deliberately omitted from the
    # base schema because the default `postgres:16-alpine` image does not
    # ship the pgvector extension. Semantic search (Phase 6/extension) adds
    # it via a follow-up migration once the image is swapped for
    # `pgvector/pgvector:pg16` — see docs/architecture.md.


class AlertEvent(Base, UUIDPKMixin):
    __tablename__ = "alert_events"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
