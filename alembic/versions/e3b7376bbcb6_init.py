"""init

Revision ID: e3b7376bbcb6
Revises: fb8f1aa272f4
Create Date: 2026-07-02 16:59:47.738785

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3b7376bbcb6'
down_revision: Union[str, Sequence[str], None] = 'fb8f1aa272f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
