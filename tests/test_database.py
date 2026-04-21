"""
测试数据库 DDL 和数据迁移

Task #2 - Sprint 1
TDD: 先写测试，再实现
"""

import pytest
import os
from pathlib import Path
from typing import Dict, Any, List


class TestAlembicConfig:
    """测试 Alembic 迁移配置"""

    @pytest.fixture
    def alembic_ini(self) -> str:
        """读取 alembic.ini 配置"""
        ini_path = Path(__file__).parent.parent / "alembic.ini"
        with open(ini_path, "r", encoding="utf-8") as f:
            return f.read()

    @pytest.fixture
    def env_py(self) -> str:
        """读取 alembic/env.py 配置"""
        env_path = Path(__file__).parent.parent / "alembic" / "env.py"
        with open(env_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_alembic_ini_exists(self):
        """测试 alembic.ini 文件存在"""
        ini_path = Path(__file__).parent.parent / "alembic.ini"
        assert ini_path.exists(), "alembic.ini 应该存在"

    def test_alembic_directory_exists(self):
        """测试 alembic 目录存在"""
        alembic_dir = Path(__file__).parent.parent / "alembic"
        assert alembic_dir.exists(), "alembic 目录应该存在"
        assert alembic_dir.is_dir(), "alembic 应该是一个目录"

    def test_versions_directory_exists(self):
        """测试 versions 目录存在"""
        versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
        assert versions_dir.exists(), "alembic/versions 目录应该存在"

    def test_script_py_mako_exists(self):
        """测试 script.py.mako 模板存在"""
        script_path = Path(__file__).parent.parent / "alembic" / "script.py.mako"
        assert script_path.exists(), "script.py.mako 应该存在"

    def test_alembic_ini_database_url(self, alembic_ini):
        """测试 alembic.ini 数据库 URL 配置"""
        assert "sqlalchemy.url" in alembic_ini, "alembic.ini 应该配置 sqlalchemy.url"

    def test_env_py_target_metadata(self, env_py):
        """测试 env.py 导入 target_metadata"""
        assert "target_metadata" in env_py, "env.py 应该导入 target_metadata"
        assert "Base.metadata" in env_py or "models" in env_py, "env.py 应该引用模型元数据"


class TestDatabaseModels:
    """测试数据库模型"""

    @pytest.fixture
    def models_init(self) -> str:
        """读取 app/models/__init__.py"""
        models_path = Path(__file__).parent.parent / "app" / "models" / "__init__.py"
        with open(models_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_models_directory_exists(self):
        """测试 app/models 目录存在"""
        models_dir = Path(__file__).parent.parent / "app" / "models"
        assert models_dir.exists(), "app/models 目录应该存在"

    def test_user_model_exists(self):
        """测试 User 模型文件存在"""
        user_path = Path(__file__).parent.parent / "app" / "models" / "user.py"
        assert user_path.exists(), "app/models/user.py 应该存在"

    def test_recipe_model_exists(self):
        """测试 Recipe 模型文件存在"""
        recipe_path = Path(__file__).parent.parent / "app" / "models" / "recipe.py"
        assert recipe_path.exists(), "app/models/recipe.py 应该存在"

    def test_models_init_exports_all(self, models_init):
        """测试 models/__init__.py 导出所有模型"""
        assert "User" in models_init, "应该导出 User 模型"
        assert "Recipe" in models_init, "应该导出 Recipe 模型"
        assert "RecipeIngredient" in models_init, "应该导出 RecipeIngredient 模型"
        assert "RecipeStep" in models_init, "应该导出 RecipeStep 模型"


class TestUserModel:
    """测试 User 模型定义"""

    @pytest.fixture
    def user_model(self) -> str:
        """读取 app/models/user.py"""
        user_path = Path(__file__).parent.parent / "app" / "models" / "user.py"
        with open(user_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_user_table_name(self, user_model):
        """测试 User 表名配置"""
        assert "__tablename__" in user_model, "User 应该配置 __tablename__"
        assert "users" in user_model, "表名应该是 users"

    def test_user_id_field(self, user_model):
        """测试 User.id 字段"""
        assert "id" in user_model, "User 应该有 id 字段"
        assert "UUID" in user_model or "uuid" in user_model.lower(), "id 应该是 UUID 类型"
        assert "primary_key" in user_model.lower() or "primarykey" in user_model.lower(), "id 应该是主键"

    def test_user_phone_field(self, user_model):
        """测试 User.phone 字段"""
        assert "phone" in user_model, "User 应该有 phone 字段"
        assert "unique" in user_model.lower(), "phone 应该是唯一的"

    def test_user_wechat_fields(self, user_model):
        """测试微信登录字段"""
        assert "wechat" in user_model.lower(), "User 应该有微信相关字段"
        assert "openid" in user_model.lower(), "应该有 wechat_openid 字段"

    def test_user_taste_prefs_field(self, user_model):
        """测试口味偏好字段"""
        assert "taste" in user_model.lower() or "prefs" in user_model.lower(), "User 应该有口味偏好字段"

    def test_user_timestamps(self, user_model):
        """测试时间戳字段"""
        assert "created_at" in user_model, "User 应该有 created_at 字段"
        assert "updated_at" in user_model, "User 应该有 updated_at 字段"


class TestRecipeModel:
    """测试 Recipe 模型定义"""

    @pytest.fixture
    def recipe_model(self) -> str:
        """读取 app/models/recipe.py"""
        recipe_path = Path(__file__).parent.parent / "app" / "models" / "recipe.py"
        with open(recipe_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_recipe_table_name(self, recipe_model):
        """测试 Recipe 表名配置"""
        assert "__tablename__" in recipe_model, "Recipe 应该配置 __tablename__"
        assert "recipes" in recipe_model, "表名应该是 recipes"

    def test_recipe_id_field(self, recipe_model):
        """测试 Recipe.id 字段"""
        assert "id" in recipe_model, "Recipe 应该有 id 字段"
        assert "UUID" in recipe_model or "uuid" in recipe_model.lower(), "id 应该是 UUID 类型"

    def test_recipe_name_field(self, recipe_model):
        """测试 Recipe.name 字段"""
        assert "name" in recipe_model, "Recipe 应该有 name 字段"

    def test_recipe_cuisine_field(self, recipe_model):
        """测试菜系字段"""
        assert "cuisine" in recipe_model, "Recipe 应该有 cuisine 字段"

    def test_recipe_difficulty_field(self, recipe_model):
        """测试难度字段"""
        assert "difficulty" in recipe_model, "Recipe 应该有 difficulty 字段"
        assert "easy" in recipe_model.lower() or "medium" in recipe_model.lower(), "难度应该有限制"

    def test_recipe_time_fields(self, recipe_model):
        """测试时间字段"""
        assert "prep_time" in recipe_model or "preptime" in recipe_model.lower(), "Recipe 应该有 prep_time 字段"
        assert "cook_time" in recipe_model or "cooktime" in recipe_model.lower(), "Recipe 应该有 cook_time 字段"

    def test_recipe_tags_field(self, recipe_model):
        """测试标签字段"""
        assert "tags" in recipe_model, "Recipe 应该有 tags 字段"
        assert "JSON" in recipe_model or "json" in recipe_model or "JSONB" in recipe_model, "tags 应该是 JSON 类型"

    def test_recipe_vector_id_field(self, recipe_model):
        """测试向量 ID 字段"""
        assert "vector_id" in recipe_model, "Recipe 应该有 vector_id 字段"

    def test_recipe_foreign_key_user(self, recipe_model):
        """测试用户外键关联"""
        assert "user_id" in recipe_model, "Recipe 应该有 user_id 字段"
        assert "ForeignKey" in recipe_model or "foreign_key" in recipe_model.lower(), "user_id 应该是外键"

    def test_recipe_timestamps(self, recipe_model):
        """测试时间戳字段"""
        assert "created_at" in recipe_model, "Recipe 应该有 created_at 字段"
        assert "updated_at" in recipe_model, "Recipe 应该有 updated_at 字段"


class TestRecipeIngredientModel:
    """测试 RecipeIngredient 模型定义"""

    @pytest.fixture
    def ingredient_model(self) -> str:
        """读取 app/models/ingredient.py"""
        ingredient_path = Path(__file__).parent.parent / "app" / "models" / "ingredient.py"
        with open(ingredient_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_ingredient_model_file_exists(self):
        """测试 Ingredient 模型文件存在"""
        ingredient_path = Path(__file__).parent.parent / "app" / "models" / "ingredient.py"
        assert ingredient_path.exists(), "app/models/ingredient.py 应该存在"

    def test_ingredient_table_name(self, ingredient_model):
        """测试表名配置"""
        assert "__tablename__" in ingredient_model, "应该配置 __tablename__"
        assert "recipe_ingredients" in ingredient_model or "ingredients" in ingredient_model, "表名应该包含 recipe_ingredients"

    def test_ingredient_id_field(self, ingredient_model):
        """测试 id 字段"""
        assert "id" in ingredient_model, "应该有 id 字段"

    def test_ingredient_recipe_fk(self, ingredient_model):
        """测试菜谱外键"""
        assert "recipe_id" in ingredient_model, "应该有 recipe_id 字段"
        assert "ForeignKey" in ingredient_model or "foreign_key" in ingredient_model.lower(), "recipe_id 应该是外键"
        assert "CASCADE" in ingredient_model.upper() or "cascade" in ingredient_model.lower(), "应该配置级联删除"

    def test_ingredient_name_field(self, ingredient_model):
        """测试食材名称字段"""
        assert "name" in ingredient_model, "应该有 name 字段"

    def test_ingredient_amount_field(self, ingredient_model):
        """测试用量字段"""
        assert "amount" in ingredient_model, "应该有 amount 字段"

    def test_ingredient_unit_field(self, ingredient_model):
        """测试单位字段"""
        assert "unit" in ingredient_model, "应该有 unit 字段"

    def test_ingredient_sequence_field(self, ingredient_model):
        """测试排序字段"""
        assert "sequence" in ingredient_model, "应该有 sequence 字段"


class TestRecipeStepModel:
    """测试 RecipeStep 模型定义"""

    @pytest.fixture
    def step_model(self) -> str:
        """读取 app/models/step.py"""
        step_path = Path(__file__).parent.parent / "app" / "models" / "step.py"
        with open(step_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_step_model_file_exists(self):
        """测试 Step 模型文件存在"""
        step_path = Path(__file__).parent.parent / "app" / "models" / "step.py"
        assert step_path.exists(), "app/models/step.py 应该存在"

    def test_step_table_name(self, step_model):
        """测试表名配置"""
        assert "__tablename__" in step_model, "应该配置 __tablename__"
        assert "recipe_steps" in step_model or "steps" in step_model, "表名应该包含 recipe_steps"

    def test_step_id_field(self, step_model):
        """测试 id 字段"""
        assert "id" in step_model, "应该有 id 字段"

    def test_step_recipe_fk(self, step_model):
        """测试菜谱外键"""
        assert "recipe_id" in step_model, "应该有 recipe_id 字段"
        assert "ForeignKey" in step_model or "foreign_key" in step_model.lower(), "recipe_id 应该是外键"
        assert "CASCADE" in step_model.upper() or "cascade" in step_model.lower(), "应该配置级联删除"

    def test_step_step_no_field(self, step_model):
        """测试步骤序号字段"""
        assert "step_no" in step_model, "应该有 step_no 字段"

    def test_step_description_field(self, step_model):
        """测试步骤描述字段"""
        assert "description" in step_model, "应该有 description 字段"

    def test_step_duration_field(self, step_model):
        """测试耗时段字段"""
        assert "duration" in step_model.lower(), "应该有 duration_seconds 字段"


class TestMigrationFiles:
    """测试迁移文件"""

    @pytest.fixture
    def versions_dir(self) -> Path:
        """获取 versions 目录"""
        return Path(__file__).parent.parent / "alembic" / "versions"

    def test_initial_migration_exists(self, versions_dir):
        """测试初始迁移文件存在"""
        migration_files = list(versions_dir.glob("*_*.py"))
        assert len(migration_files) > 0, "应该至少有一个迁移文件"

    def test_migration_has_revision(self, versions_dir):
        """测试迁移文件有 revision 标识"""
        migration_files = list(versions_dir.glob("*.py"))
        has_revision = False
        for f in migration_files:
            with open(f, "r", encoding="utf-8") as file:
                content = file.read()
                if "revision" in content and "down_revision" in content:
                    has_revision = True
                    break
        assert has_revision, "迁移文件应该有 revision 和 down_revision"

    def test_migration_has_upgrade_function(self, versions_dir):
        """测试迁移文件有 upgrade 函数"""
        migration_files = list(versions_dir.glob("*.py"))
        has_upgrade = False
        for f in migration_files:
            with open(f, "r", encoding="utf-8") as file:
                content = file.read()
                if "def upgrade()" in content:
                    has_upgrade = True
                    break
        assert has_upgrade, "迁移文件应该有 upgrade() 函数"

    def test_migration_has_downgrade_function(self, versions_dir):
        """测试迁移文件有 downgrade 函数"""
        migration_files = list(versions_dir.glob("*.py"))
        has_downgrade = False
        for f in migration_files:
            with open(f, "r", encoding="utf-8") as file:
                content = file.read()
                if "def downgrade()" in content:
                    has_downgrade = True
                    break
        assert has_downgrade, "迁移文件应该有 downgrade() 函数"


class TestDatabaseConnection:
    """测试数据库连接配置"""

    @pytest.fixture
    def config_file(self) -> str:
        """读取 app/core/config.py"""
        config_path = Path(__file__).parent.parent / "app" / "core" / "config.py"
        with open(config_path, "r", encoding="utf-8") as f:
            return f.read()

    @pytest.fixture
    def database_file(self) -> str:
        """读取 app/core/database.py"""
        db_path = Path(__file__).parent.parent / "app" / "core" / "database.py"
        with open(db_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_config_file_exists(self):
        """测试配置文件存在"""
        config_path = Path(__file__).parent.parent / "app" / "core" / "config.py"
        assert config_path.exists(), "app/core/config.py 应该存在"

    def test_database_file_exists(self):
        """测试数据库配置存在"""
        db_path = Path(__file__).parent.parent / "app" / "core" / "database.py"
        assert db_path.exists(), "app/core/database.py 应该存在"

    def test_database_url_config(self, config_file):
        """测试数据库 URL 配置"""
        assert "DATABASE_URL" in config_file, "应该配置 DATABASE_URL"

    def test_async_engine(self, database_file):
        """测试异步引擎配置"""
        assert "create_async_engine" in database_file or "async_engine" in database_file.lower(), "应该配置异步引擎"

    def test_session_factory(self, database_file):
        """测试会话工厂配置"""
        assert "session" in database_file.lower() or "Session" in database_file, "应该配置会话工厂"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
