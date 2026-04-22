"""add recipe_images table.

Revision ID: 004
Revises: 003
Create Date: 2026-04-22

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
    """创建 recipe_images 表."""
    op.create_table(
        'recipe_images',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('recipe_id', sa.String(36), nullable=False),
        sa.Column('step_no', sa.Integer(), nullable=True),
        sa.Column('image_type', sa.String(length=20), nullable=False),
        sa.Column('source_path', sa.String(length=500), nullable=False),
        sa.Column('local_path', sa.String(length=500), nullable=False),
        sa.Column('image_url', sa.String(length=1000), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('clip_vector_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recipe_images_id'), 'recipe_images', ['id'], unique=False)
    op.create_index(op.f('ix_recipe_images_recipe_id'), 'recipe_images', ['recipe_id'], unique=False)


def downgrade() -> None:
    """删除 recipe_images 表."""
    op.drop_index(op.f('ix_recipe_images_recipe_id'), table_name='recipe_images')
    op.drop_index(op.f('ix_recipe_images_id'), table_name='recipe_images')
    op.drop_table('recipe_images')
