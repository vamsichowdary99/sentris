import uuid

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import MitreMappingSource


class MitreTechnique(Base, TimestampMixin):
    """Seeded reference data — ATT&CK technique ID is the natural key."""

    __tablename__ = "mitre_techniques"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # e.g. "T1110" / "T1110.001"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tactic: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)


class AlertMitreTechnique(Base):
    __tablename__ = "alert_mitre"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), primary_key=True
    )
    technique_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("mitre_techniques.id", ondelete="CASCADE"), primary_key=True
    )
    source: Mapped[MitreMappingSource] = mapped_column(
        Enum(MitreMappingSource, name="mitre_mapping_source"), nullable=False
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
