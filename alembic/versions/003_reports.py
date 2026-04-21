"""add reports table and recipe.report_count

Revision ID: 003
Revises: 002
Create Date: 2026-04-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 reports 表和 recipe.report_count 字段."""
    # 添加 report_count 字段到 recipes 表
    op.add_column('recipes', sa.Column('report_count', sa.Integer(), nullable=False, server_default='0'))

    # 创建 reports 表
    op.create_table(
        'reports',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('recipe_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('reason', sa.String(1024), nullable=False, comment='举报原因'),
        sa.Column('status', sa.String(32), nullable=True, default='pending', comment='举报状态：pending/processed'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建索引
    op.create_index('ix_reports_recipe_id', 'reports', ['recipe_id'])
    op.create_index('ix_reports_created_at', 'reports', ['created_at'])


def downgrade() -> None:
    """回滚迁移."""
    op.drop_index('ix_reports_created_at', table_name='reports')
    op.drop_index('ix_reports_recipe_id', table_name='reports')
    op.drop_table('reports')
    op.drop_column('recipes', 'report_count')
