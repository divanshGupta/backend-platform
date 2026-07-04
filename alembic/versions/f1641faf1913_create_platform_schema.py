"""create platform schema

Revision ID: f1641faf1913
Revises: e3b7376bbcb6
Create Date: 2026-07-02 20:46:50.088209

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1641faf1913'
down_revision: Union[str, Sequence[str], None] = 'e3b7376bbcb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE SCHEMA IF NOT EXISTS platform")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP SCHEMA IF EXISTS platform CASCADE")
