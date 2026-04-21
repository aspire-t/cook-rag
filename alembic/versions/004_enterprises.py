"""add enterprises and enterprise_users tables

Revision ID: 004
Revises: 003
Create Date: 2026-04-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 enterprises 和 enterprise_users 表."""
    # 创建 enterprises 表
    op.create_table(
        'enterprises',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False, comment='企业名称'),
        sa.Column('unified_social_credit_code', sa.String(50), nullable=True, comment='统一社会信用代码'),
        sa.Column('legal_representative', sa.String(100), nullable=True, comment='法人代表'),
        sa.Column('contact_phone', sa.String(20), nullable=True),
        sa.Column('contact_email', sa.String(100), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False, comment='是否已认证'),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True, comment='是否激活'),
        sa.Column('plan_type', sa.String(20), nullable=False, default='basic', comment='套餐类型'),
        sa.Column('plan_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建 enterprise_users 表
    op.create_table(
        'enterprise_users',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('enterprise_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, default='member', comment='角色'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, default=False, comment='是否为主企业'),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True, comment='是否激活'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['enterprise_id'], ['enterprises.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建索引
    op.create_index('ix_enterprise_users_user_id', 'enterprise_users', ['user_id'])
    op.create_index('ix_enterprise_users_enterprise_id', 'enterprise_users', ['enterprise_id'])
    op.create_index('ix_enterprise_users_user_enterprise', 'enterprise_users', ['user_id', 'enterprise_id'], unique=True)


def downgrade() -> None:
    """回滚迁移."""
    op.drop_index('ix_enterprise_users_user_enterprise', table_name='enterprise_users')
    op.drop_index('ix_enterprise_users_enterprise_id', table_name='enterprise_users')
    op.drop_index('ix_enterprise_users_user_id', table_name='enterprise_users')
    op.drop_table('enterprise_users')
    op.drop_table('enterprises')
