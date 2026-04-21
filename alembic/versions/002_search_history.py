"""Add search_history table

Revision ID: 002_search_history
Revises: 001_initial
Create Date: 2026-04-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_search_history'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create search_history table
    op.create_table(
        'search_history',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=True),
        sa.Column('session_id', sa.String(64), nullable=True),
        sa.Column('query', sa.String(512), nullable=False),
        sa.Column('filters', sa.String(2048), nullable=True),
        sa.Column('result_count', sa.Integer, nullable=True, default=0),
        sa.Column('clicked_recipe_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes
    op.create_index('ix_search_history_user_id', 'search_history', ['user_id'])
    op.create_index('ix_search_history_session_id', 'search_history', ['session_id'])
    op.create_index('ix_search_history_created_at', 'search_history', ['created_at'])
    op.create_index('ix_search_history_user_created', 'search_history', ['user_id', 'created_at'])
    op.create_index('ix_search_history_session_created', 'search_history', ['session_id', 'created_at'])

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_search_history_user_id',
        'search_history', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint('fk_search_history_user_id', 'search_history', type_='foreignkey')

    # Drop indexes
    op.drop_index('ix_search_history_session_created')
    op.drop_index('ix_search_history_user_created')
    op.drop_index('ix_search_history_created_at')
    op.drop_index('ix_search_history_session_id')
    op.drop_index('ix_search_history_user_id')

    # Drop table
    op.drop_table('search_history')
