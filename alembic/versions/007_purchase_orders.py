"""add suppliers and purchase_orders tables

Revision ID: 007
Revises: 006
Create Date: 2026-04-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 suppliers 和 purchase_orders 表."""
    # 创建 suppliers 表
    op.create_table(
        'suppliers',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('enterprise_id', sa.UUID(as_uuid=True), nullable=False, comment='企业 ID'),
        sa.Column('name', sa.String(200), nullable=False, comment='供应商名称'),
        sa.Column('contact_person', sa.String(100), nullable=True, comment='联系人'),
        sa.Column('contact_phone', sa.String(20), nullable=True, comment='联系电话'),
        sa.Column('contact_email', sa.String(100), nullable=True, comment='联系邮箱'),
        sa.Column('address', sa.String(500), nullable=True, comment='地址'),
        sa.Column('categories', sa.JSON(), nullable=False, default=list, comment='供应品类列表'),
        sa.Column('price_list', sa.JSON(), nullable=False, default=dict, comment='价格表'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True, comment='是否激活'),
        sa.Column('rating', sa.Numeric(3, 2), nullable=True, comment='评级 (1.0-5.0)'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['enterprise_id'], ['enterprises.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建 purchase_orders 表
    op.create_table(
        'purchase_orders',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('enterprise_id', sa.UUID(as_uuid=True), nullable=False, comment='企业 ID'),
        sa.Column('supplier_id', sa.UUID(as_uuid=True), nullable=False, comment='供应商 ID'),
        sa.Column('order_number', sa.String(50), nullable=False, comment='订单号'),
        sa.Column('status', sa.String(20), nullable=False, default='pending', comment='状态'),
        sa.Column('order_date', sa.Date(), nullable=False, comment='下单日期'),
        sa.Column('expected_date', sa.Date(), nullable=True, comment='预计到货日期'),
        sa.Column('received_date', sa.Date(), nullable=True, comment='实际到货日期'),
        sa.Column('items', sa.JSON(), nullable=False, comment='订单物品列表'),
        sa.Column('total_amount', sa.Numeric(10, 2), nullable=False, default=0, comment='总金额'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_by', sa.UUID(as_uuid=True), nullable=True, comment='创建人 ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['enterprise_id'], ['enterprises.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建索引
    op.create_index('ix_suppliers_enterprise_id', 'suppliers', ['enterprise_id'])
    op.create_index('ix_suppliers_name', 'suppliers', ['name'])

    op.create_index('ix_purchase_orders_enterprise_id', 'purchase_orders', ['enterprise_id'])
    op.create_index('ix_purchase_orders_supplier_id', 'purchase_orders', ['supplier_id'])
    op.create_index('ix_purchase_orders_status', 'purchase_orders', ['status'])
    op.create_index('ix_purchase_orders_order_date', 'purchase_orders', ['order_date'])
    op.create_index('ix_purchase_orders_order_number', 'purchase_orders', ['order_number'], unique=True)


def downgrade() -> None:
    """回滚迁移."""
    op.drop_index('ix_purchase_orders_order_number', table_name='purchase_orders')
    op.drop_index('ix_purchase_orders_order_date', table_name='purchase_orders')
    op.drop_index('ix_purchase_orders_status', table_name='purchase_orders')
    op.drop_index('ix_purchase_orders_supplier_id', table_name='purchase_orders')
    op.drop_index('ix_purchase_orders_enterprise_id', table_name='purchase_orders')
    op.drop_index('ix_suppliers_name', table_name='suppliers')
    op.drop_index('ix_suppliers_enterprise_id', table_name='suppliers')
    op.drop_table('purchase_orders')
    op.drop_table('suppliers')
