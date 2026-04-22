"""
测试 RecipeImage 模型

TDD: 先写失败的测试，再实现代码
"""

import pytest
from pathlib import Path


class TestRecipeImageModel:
    """测试 RecipeImage 模型"""

    @pytest.fixture
    def recipe_image_module(self) -> str:
        """读取 app/models/recipe_image.py"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "recipe_image.py"
        with open(model_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_recipe_image_model_exists(self):
        """测试 RecipeImage 模型文件存在"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "recipe_image.py"
        assert model_path.exists(), "app/models/recipe_image.py 应该存在"

    def test_recipe_image_class_defined(self, recipe_image_module):
        """测试 RecipeImage 类定义"""
        assert "class RecipeImage" in recipe_image_module, "应该定义 RecipeImage 类"
        assert "Base" in recipe_image_module, "RecipeImage 应该继承 Base"

    def test_tablename_defined(self, recipe_image_module):
        """测试表名定义"""
        assert '__tablename__ = "recipe_images"' in recipe_image_module, "应该定义 __tablename__"

    def test_primary_key_field(self, recipe_image_module):
        """测试主键字段 id"""
        assert "primary_key=True" in recipe_image_module, "应该有主键字段"

    def test_recipe_id_foreign_key(self, recipe_image_module):
        """测试外键 recipe_id"""
        assert "recipe_id" in recipe_image_module, "应该有 recipe_id 字段"
        assert "ForeignKey" in recipe_image_module, "应该有外键约束"
        assert "recipes.id" in recipe_image_module, "外键应该引用 recipes.id"
        assert "ondelete=" in recipe_image_module, "应该有 ON DELETE 约束"

    def test_image_type_field(self, recipe_image_module):
        """测试 image_type 字段"""
        assert "image_type" in recipe_image_module, "应该有 image_type 字段"

    def test_image_url_field(self, recipe_image_module):
        """测试 image_url 字段"""
        assert "image_url" in recipe_image_module, "应该有 image_url 字段"

    def test_source_path_field(self, recipe_image_module):
        """测试 source_path 字段"""
        assert "source_path" in recipe_image_module, "应该有 source_path 字段"

    def test_local_path_field(self, recipe_image_module):
        """测试 local_path 字段"""
        assert "local_path" in recipe_image_module, "应该有 local_path 字段"

    def test_clip_vector_id_field(self, recipe_image_module):
        """测试 clip_vector_id 字段"""
        assert "clip_vector_id" in recipe_image_module, "应该有 clip_vector_id 字段"

    def test_created_at_field(self, recipe_image_module):
        """测试 created_at 字段"""
        assert "created_at" in recipe_image_module, "应该有 created_at 字段"
        assert "DateTime" in recipe_image_module, "created_at 应该是 DateTime 类型"

    def test_relationship_defined(self, recipe_image_module):
        """测试关联关系定义"""
        assert "relationship" in recipe_image_module, "应该有 relationship"
        assert "back_populates" in recipe_image_module, "应该定义 back_populates"


class TestRecipeModelUpdate:
    """测试 Recipe 模型更新"""

    @pytest.fixture
    def recipe_model(self) -> str:
        """读取 app/models/recipe.py"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "recipe.py"
        with open(model_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_images_relationship_in_recipe(self, recipe_model):
        """测试 Recipe 模型中 images 关联关系"""
        assert "images" in recipe_model, "Recipe 模型应该有 images 关联"
        assert "RecipeImage" in recipe_model, "Recipe 模型应该引用 RecipeImage"


class TestModelsInit:
    """测试 models/__init__.py 导出"""

    @pytest.fixture
    def models_init(self) -> str:
        """读取 app/models/__init__.py"""
        init_path = Path(__file__).parent.parent / "app" / "models" / "__init__.py"
        with open(init_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_recipe_image_imported(self, models_init):
        """测试 RecipeImage 被导入"""
        assert "RecipeImage" in models_init, "应该导入 RecipeImage"

    def test_recipe_image_in_all(self, models_init):
        """测试 RecipeImage 在 __all__ 中"""
        assert '"RecipeImage"' in models_init or "'RecipeImage'" in models_init, "__all__ 应该包含 RecipeImage"


class TestAlembicMigration:
    """测试 Alembic 迁移文件"""

    @pytest.fixture
    def migration_file(self) -> str:
        """读取 alembic/versions/004_recipe_images.py"""
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "004_recipe_images.py"
        with open(migration_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_migration_file_exists(self):
        """测试迁移文件存在"""
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "004_recipe_images.py"
        assert migration_path.exists(), "alembic/versions/004_recipe_images.py 应该存在"

    def test_revision_defined(self, migration_file):
        """测试 revision 定义"""
        assert "revision" in migration_file, "应该有 revision"
        assert "'004'" in migration_file, "revision 应该是 '004'"

    def test_down_revision_defined(self, migration_file):
        """测试 down_revision 定义"""
        assert "down_revision" in migration_file, "应该有 down_revision"
        assert "'003'" in migration_file, "down_revision 应该是 '003'"

    def test_upgrade_function_exists(self, migration_file):
        """测试 upgrade 函数存在"""
        assert "def upgrade()" in migration_file, "应该有 upgrade 函数"

    def test_downgrade_function_exists(self, migration_file):
        """测试 downgrade 函数存在"""
        assert "def downgrade()" in migration_file, "应该有 downgrade 函数"

    def test_create_recipe_images_table(self, migration_file):
        """测试创建 recipe_images 表"""
        assert "create_table" in migration_file, "应该有 create_table 调用"
        assert "'recipe_images'" in migration_file, "应该创建 recipe_images 表"

    def test_table_columns(self, migration_file):
        """测试表字段定义"""
        assert "'id'" in migration_file, "应该有 id 字段"
        assert "'recipe_id'" in migration_file, "应该有 recipe_id 字段"
        assert "'image_type'" in migration_file, "应该有 image_type 字段"
        assert "'image_url'" in migration_file, "应该有 image_url 字段"
        assert "'source_path'" in migration_file, "应该有 source_path 字段"
        assert "'local_path'" in migration_file, "应该有 local_path 字段"
        assert "'clip_vector_id'" in migration_file, "应该有 clip_vector_id 字段"
        assert "'created_at'" in migration_file, "应该有 created_at 字段"

    def test_foreign_key_constraint(self, migration_file):
        """测试外键约束"""
        assert "ForeignKeyConstraint" in migration_file, "应该有 ForeignKeyConstraint"
        assert "ondelete=" in migration_file, "应该有 ON DELETE 约束"

    def test_indexes_created(self, migration_file):
        """测试索引创建"""
        assert "create_index" in migration_file, "应该有 create_index 调用"
        assert "recipe_id" in migration_file, "应该有 recipe_id 索引"


class TestConfigUpdate:
    """测试配置文件更新"""

    @pytest.fixture
    def config_file(self) -> str:
        """读取 app/core/config.py"""
        config_path = Path(__file__).parent.parent / "app" / "core" / "config.py"
        with open(config_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_image_repo_name_config(self, config_file):
        """测试 IMAGE_REPO_NAME 配置"""
        assert "IMAGE_REPO_NAME" in config_file, "应该有 IMAGE_REPO_NAME 配置"
        assert "cook-rag-images" in config_file, "IMAGE_REPO_NAME 应该是 'cook-rag-images'"

    def test_image_repo_owner_config(self, config_file):
        """测试 IMAGE_REPO_OWNER 配置"""
        assert "IMAGE_REPO_OWNER" in config_file, "应该有 IMAGE_REPO_OWNER 配置"
        assert "aspire-t" in config_file, "IMAGE_REPO_OWNER 应该是 'aspire-t'"

    def test_image_base_cdn_url_config(self, config_file):
        """测试 IMAGE_BASE_CDN_URL 配置"""
        assert "IMAGE_BASE_CDN_URL" in config_file, "应该有 IMAGE_BASE_CDN_URL 配置"
        assert "cdn.jsdelivr.net" in config_file, "IMAGE_BASE_CDN_URL 应该包含 cdn.jsdelivr.net"

    def test_clip_model_name_config(self, config_file):
        """测试 CLIP_MODEL_NAME 配置"""
        assert "CLIP_MODEL_NAME" in config_file, "应该有 CLIP_MODEL_NAME 配置"
        assert "chinese-clip-vit-base-patch16" in config_file, "应该有 CLIP 模型名称"

    def test_clip_device_config(self, config_file):
        """测试 CLIP_DEVICE 配置"""
        assert "CLIP_DEVICE" in config_file, "应该有 CLIP_DEVICE 配置"
