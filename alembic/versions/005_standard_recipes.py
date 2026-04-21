"""add standard_recipes table

Revision ID: 005
Revises: 004
Create Date: 2026-04-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 standard_recipes 表."""
    op.create_table(
        'standard_recipes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('recipe_id', sa.String(36), nullable=False, comment='关联菜谱 ID'),
        sa.Column('enterprise_id', sa.String(36), nullable=False, comment='所属企业 ID'),
        sa.Column('sop_document_url', sa.String(255), nullable=True, comment='SOP 文档存储路径'),
        sa.Column('sop_content', sa.Text(), nullable=True, comment='SOP 内容（JSON 格式）'),
        sa.Column('cost_calculation', sa.Text(), nullable=True, comment='成本核算数据（JSON 格式）'),
        sa.Column('total_cost', sa.Float(), nullable=True, comment='总成本（元）'),
        sa.Column('suggested_price', sa.Float(), nullable=True, comment='建议售价（元）'),
        sa.Column('gross_margin', sa.Float(), nullable=True, comment='毛利率（%）'),
        sa.Column('nutrition_info', sa.Text(), nullable=True, comment='营养成分数据（JSON 格式）'),
        sa.Column('allergen_info', sa.Text(), nullable=True, comment='过敏原信息（JSON 格式）'),
        sa.Column('shelf_life_days', sa.Integer(), nullable=True, comment='保质期天数'),
        sa.Column('storage_temperature', sa.String(50), nullable=True, comment='储存温度要求'),
        sa.Column('version', sa.Integer(), default=1, nullable=False, comment='版本号'),
        sa.Column('is_latest', sa.Boolean(), default=True, nullable=False, comment='是否为最新版本'),
        sa.Column('created_by', sa.String(36), nullable=False, comment='创建人 ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['enterprise_id'], ['enterprises.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建索引
    op.create_index('ix_standard_recipes_recipe_id', 'standard_recipes', ['recipe_id'])
    op.create_index('ix_standard_recipes_enterprise_id', 'standard_recipes', ['enterprise_id'])
    op.create_index('ix_standard_recipes_is_latest', 'standard_recipes', ['is_latest'])


def downgrade() -> None:
    """回滚迁移."""
    op.drop_index('ix_standard_recipes_is_latest', table_name='standard_recipes')
    op.drop_index('ix_standard_recipes_enterprise_id', table_name='standard_recipes')
    op.drop_index('ix_standard_recipes_recipe_id', table_name='standard_recipes')
    op.drop_table('standard_recipes')
