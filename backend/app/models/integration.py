import uuid
from typing import Any

from sqlalchemy import Boolean, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import IntegrationKind


class Integration(Base, UUIDPKMixin, TimestampMixin):
    """Per-org provider configuration.

    `config` holds provider settings; any secret values (API keys, webhook
    URLs) MUST be Fernet-encrypted at the application layer before being
    written here — never store plaintext secrets in this column.
    """

    __tablename__ = "integrations"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[IntegrationKind] = mapped_column(
        Enum(IntegrationKind, name="integration_kind"), nullable=False
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
