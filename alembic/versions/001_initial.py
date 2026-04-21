"""Initial migration - create users, recipes, recipe_ingredients, recipe_steps tables

Revision ID: 001_initial
Revises:
Create Date: 2026-04-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('nickname', sa.String(length=50), nullable=True),
        sa.Column('avatar_url', sa.String(length=255), nullable=True),
        sa.Column('taste_prefs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=dict),
        sa.Column('dietary_restrictions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=list),
        sa.Column('wechat_openid', sa.String(length=100), nullable=True),
        sa.Column('wechat_unionid', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone')
    )
    op.create_index('idx_users_phone', 'users', ['phone'], unique=False)
    op.create_index('idx_users_wechat', 'users', ['wechat_openid'], unique=False)
    op.create_index('idx_users_taste_prefs', 'users', ['taste_prefs'], unique=False, postgresql_using='gin')

    # Create recipes table
    op.create_table(
        'recipes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('enterprise_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('cuisine', sa.String(length=50), nullable=True),
        sa.Column('difficulty', sa.String(length=20), nullable=True),
        sa.Column('prep_time', sa.Integer(), nullable=True),
        sa.Column('cook_time', sa.Integer(), nullable=True),
        sa.Column('servings', sa.Integer(), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=list),
        sa.Column('source_url', sa.String(length=255), nullable=True),
        sa.Column('source_type', sa.String(length=20), nullable=False, default='system'),
        sa.Column('is_public', sa.Boolean(), nullable=False, default=True),
        sa.Column('audit_status', sa.String(length=20), nullable=False, default='approved'),
        sa.Column('rejected_reason', sa.Text(), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=False, default=0),
        sa.Column('favorite_count', sa.Integer(), nullable=False, default=0),
        sa.Column('vector_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name='check_difficulty'),
        sa.CheckConstraint('prep_time >= 0', name='check_prep_time'),
        sa.CheckConstraint('cook_time >= 0', name='check_cook_time'),
        sa.CheckConstraint('servings > 0', name='check_servings')
    )
    op.create_index('idx_recipes_user', 'recipes', ['user_id'], unique=False)
    op.create_index('idx_recipes_cuisine', 'recipes', ['cuisine'], unique=False)
    op.create_index('idx_recipes_difficulty', 'recipes', ['difficulty'], unique=False)
    op.create_index('idx_recipes_tags', 'recipes', ['tags'], unique=False, postgresql_using='gin')
    op.create_index('idx_recipes_vector_id', 'recipes', ['vector_id'], unique=False, postgresql_where=sa.text('vector_id IS NOT NULL'))

    # Create recipe_ingredients table
    op.create_table(
        'recipe_ingredients',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recipe_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('amount', postgresql.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('unit', sa.String(length=20), nullable=True),
        sa.Column('sequence', sa.Integer(), nullable=False, default=0),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('recipe_id', 'name', 'sequence', name='idx_recipe_ingredients_unique')
    )
    op.create_index('idx_recipe_ingredients_recipe', 'recipe_ingredients', ['recipe_id'], unique=False)
    op.create_index('idx_recipe_ingredients_name', 'recipe_ingredients', ['name'], unique=False, postgresql_using='gin')

    # Create recipe_steps table
    op.create_table(
        'recipe_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recipe_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_no', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('tips', sa.Text(), nullable=True),
        sa.Column('image_url', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('recipe_id', 'step_no', name='idx_recipe_steps_unique')
    )
    op.create_index('idx_recipe_steps_recipe', 'recipe_steps', ['recipe_id'], unique=False)

    # Create function for updating updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create triggers
    op.execute("""
        CREATE TRIGGER trg_users_updated
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column()
    """)

    op.execute("""
        CREATE TRIGGER trg_recipes_updated
        BEFORE UPDATE ON recipes
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS trg_recipes_updated ON recipes')
    op.execute('DROP TRIGGER IF EXISTS trg_users_updated ON users')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')

    # Drop tables in reverse order
    op.drop_table('recipe_steps')
    op.drop_table('recipe_ingredients')
    op.drop_table('recipes')
    op.drop_table('users')
