"""add inventory and inventory_transactions tables

Revision ID: 006
Revises: 005
Create Date: 2026-04-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 inventory 和 inventory_transactions 表."""
    # 创建 inventory 表
    op.create_table(
        'inventory',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('enterprise_id', sa.UUID(as_uuid=True), nullable=False, comment='企业 ID'),
        sa.Column('ingredient_name', sa.String(100), nullable=False, comment='食材名称'),
        sa.Column('quantity', sa.Numeric(10, 2), nullable=False, default=0, comment='当前库存数量'),
        sa.Column('unit', sa.String(20), nullable=False, comment='单位'),
        sa.Column('min_stock', sa.Numeric(10, 2), nullable=True, comment='最低库存警戒线'),
        sa.Column('max_stock', sa.Numeric(10, 2), nullable=True, comment='最高库存警戒线'),
        sa.Column('expiry_date', sa.Date(), nullable=True, comment='保质期日期'),
        sa.Column('batch_number', sa.String(50), nullable=True, comment='批次号'),
        sa.Column('location', sa.String(100), nullable=True, comment='库位'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['enterprise_id'], ['enterprises.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建 inventory_transactions 表
    op.create_table(
        'inventory_transactions',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('enterprise_id', sa.UUID(as_uuid=True), nullable=False, comment='企业 ID'),
        sa.Column('inventory_id', sa.UUID(as_uuid=True), nullable=True, comment='库存 ID'),
        sa.Column('ingredient_name', sa.String(100), nullable=False, comment='食材名称'),
        sa.Column('change_quantity', sa.Numeric(10, 2), nullable=False, comment='变动数量'),
        sa.Column('transaction_type', sa.String(20), nullable=False, comment='交易类型'),
        sa.Column('before_quantity', sa.Numeric(10, 2), nullable=False, comment='变动前数量'),
        sa.Column('after_quantity', sa.Numeric(10, 2), nullable=False, comment='变动后数量'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_by', sa.UUID(as_uuid=True), nullable=True, comment='操作人 ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['enterprise_id'], ['enterprises.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['inventory_id'], ['inventory.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建索引
    op.create_index('ix_inventory_enterprise_id', 'inventory', ['enterprise_id'])
    op.create_index('ix_inventory_ingredient_name', 'inventory', ['ingredient_name'])
    op.create_index('ix_inventory_expiry_date', 'inventory', ['expiry_date'])

    op.create_index('ix_inventory_transactions_enterprise_id', 'inventory_transactions', ['enterprise_id'])
    op.create_index('ix_inventory_transactions_inventory_id', 'inventory_transactions', ['inventory_id'])


def downgrade() -> None:
    """回滚迁移."""
    op.drop_index('ix_inventory_transactions_inventory_id', table_name='inventory_transactions')
    op.drop_index('ix_inventory_transactions_enterprise_id', table_name='inventory_transactions')
    op.drop_index('ix_inventory_expiry_date', table_name='inventory')
    op.drop_index('ix_inventory_ingredient_name', table_name='inventory')
    op.drop_index('ix_inventory_enterprise_id', table_name='inventory')
    op.drop_table('inventory_transactions')
    op.drop_table('inventory')
