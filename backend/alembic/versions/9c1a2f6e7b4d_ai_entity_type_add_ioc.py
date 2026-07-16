"""ai_entity_type add ioc

Revision ID: 9c1a2f6e7b4d
Revises: 7e4b6c9a1d3f
Create Date: 2026-07-16 00:00:00.000000

Adds 'ioc' to the ai_entity_type enum so Investigate-module AI reports
(Phase 6.5) can be stored in ai_analyses the same way alert/case AI
outputs already are. Safe to run in a transaction on Postgres 12+ as
long as the new value isn't used in the same transaction (it isn't).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9c1a2f6e7b4d'
down_revision: Union[str, None] = '7e4b6c9a1d3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE ai_entity_type ADD VALUE IF NOT EXISTS 'ioc'")


def downgrade() -> None:
    # Postgres has no DROP VALUE for enums; downgrading this would require
    # rebuilding the type. Left as a no-op — acceptable for an additive,
    # backwards-compatible enum value.
    pass
