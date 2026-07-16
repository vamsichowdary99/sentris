"""search vector triggers

Revision ID: 7e4b6c9a1d3f
Revises: 38262302f50b
Create Date: 2026-07-15 00:00:00.000000

Auto-populates alerts.search_vector and cases.search_vector on
insert/update using Postgres's built-in tsvector_update_trigger, so
full-text search (GET /alerts?q=..., GET /cases?q=...) works without
every write path having to remember to compute the tsvector by hand.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7e4b6c9a1d3f'
down_revision: Union[str, None] = '38262302f50b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TRIGGER alerts_search_vector_update
        BEFORE INSERT OR UPDATE OF title, rule_name, source ON alerts
        FOR EACH ROW EXECUTE FUNCTION
        tsvector_update_trigger(search_vector, 'pg_catalog.english', title, rule_name, source)
        """
    )
    op.execute(
        """
        CREATE TRIGGER cases_search_vector_update
        BEFORE INSERT OR UPDATE OF title, summary ON cases
        FOR EACH ROW EXECUTE FUNCTION
        tsvector_update_trigger(search_vector, 'pg_catalog.english', title, summary)
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS cases_search_vector_update ON cases")
    op.execute("DROP TRIGGER IF EXISTS alerts_search_vector_update ON alerts")
