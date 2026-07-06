"""add refresh_tokens table

Revision ID: cb6b648a2a9b
Revises: 88299ab871e0
Create Date: 2026-07-06 00:05:22.063324

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb6b648a2a9b'
down_revision: Union[str, Sequence[str], None] = '88299ab871e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('refresh_tokens',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['platform.users.id'], name=op.f('fk_refresh_tokens_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_tokens')),
    schema='platform'
    )
    op.create_index(op.f('ix_platform_refresh_tokens_token_hash'), 'refresh_tokens', ['token_hash'], unique=True, schema='platform')
    op.create_index(op.f('ix_platform_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False, schema='platform')


def downgrade() -> None:
    op.drop_index(op.f('ix_platform_refresh_tokens_user_id'), table_name='refresh_tokens', schema='platform')
    op.drop_index(op.f('ix_platform_refresh_tokens_token_hash'), table_name='refresh_tokens', schema='platform')
    op.drop_table('refresh_tokens', schema='platform')
