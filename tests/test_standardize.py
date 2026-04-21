"""
测试 B 端标准化配方生成 (Task #32)

Sprint B 端 Phase 2
TDD: 测试 SOP 生成、成本核算、营养成分、过敏原信息
"""

import pytest
from pathlib import Path


class TestStandardizeModels:
    """测试标准化配方数据模型"""

    @pytest.fixture
    def standard_recipe_model_file(self) -> str:
        """读取 app/models/standard_recipe.py"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "standard_recipe.py"
        if model_path.exists():
            with open(model_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_standard_recipe_model_file_exists(self):
        """测试标准化配方模型文件存在"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "standard_recipe.py"
        assert model_path.exists(), "app/models/standard_recipe.py 应该存在"

    def test_standard_recipe_table_name(self, standard_recipe_model_file):
        """测试表名"""
        assert '__tablename__ = "standard_recipes"' in standard_recipe_model_file, "表名应该是 standard_recipes"

    def test_standard_recipe_fields(self, standard_recipe_model_file):
        """测试标准化配方的核心字段"""
        assert "recipe_id" in standard_recipe_model_file, "应该有 recipe_id 字段（关联原菜谱）"
        assert "enterprise_id" in standard_recipe_model_file, "应该有 enterprise_id 字段（所属企业）"
        assert "sop_document_url" in standard_recipe_model_file, "应该有 SOP 文档 URL 字段"
        assert "cost_calculation" in standard_recipe_model_file, "应该有成本核算字段"
        assert "nutrition_info" in standard_recipe_model_file, "应该有营养成分字段"
        assert "allergen_info" in standard_recipe_model_file, "应该有过敏原信息字段"

    def test_shelf_life_fields(self, standard_recipe_model_file):
        """测试保质期字段"""
        assert "shelf_life_days" in standard_recipe_model_file, "应该有保质期天数"
        assert "storage_temperature" in standard_recipe_model_file, "应该有储存温度"

    def test_version_control(self, standard_recipe_model_file):
        """测试版本控制"""
        assert "version" in standard_recipe_model_file, "应该有版本号"
        assert "is_latest" in standard_recipe_model_file, "应该有版本标记"


class TestStandardizeService:
    """测试标准化服务"""

    @pytest.fixture
    def standardize_service_file(self) -> str:
        """读取 app/services/standardize_service.py"""
        service_path = Path(__file__).parent.parent / "app" / "services" / "standardize_service.py"
        if service_path.exists():
            with open(service_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_standardize_service_file_exists(self):
        """测试标准化服务文件存在"""
        service_path = Path(__file__).parent.parent / "app" / "services" / "standardize_service.py"
        assert service_path.exists(), "app/services/standardize_service.py 应该存在"

    def test_llm_prompt_integration(self, standardize_service_file):
        """测试 LLM Prompt 集成"""
        assert "B_STANDARDIZE_PROMPT" in standardize_service_file or "STANDARDIZE_PROMPT" in standardize_service_file, "应该有标准化 Prompt 模板"

    def test_sop_generation(self, standardize_service_file):
        """测试 SOP 生成功能"""
        assert "generate_sop" in standardize_service_file or "sop" in standardize_service_file.lower(), "应该有 SOP 生成方法"

    def test_cost_calculation(self, standardize_service_file):
        """测试成本核算功能"""
        assert "calculate_cost" in standardize_service_file or "cost" in standardize_service_file.lower(), "应该有成本核算方法"

    def test_nutrition_analysis(self, standardize_service_file):
        """测试营养分析功能"""
        assert "nutrition" in standardize_service_file.lower(), "应该有营养分析功能"

    def test_allergen_detection(self, standardize_service_file):
        """测试过敏原检测功能"""
        assert "allergen" in standardize_service_file.lower(), "应该有过敏原检测功能"


class TestStandardizeMigration:
    """测试标准化迁移文件"""

    @pytest.fixture
    def migration_file(self) -> str:
        """读取 alembic/versions/005_standard_recipes.py"""
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "005_standard_recipes.py"
        if migration_path.exists():
            with open(migration_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_migration_file_exists(self):
        """测试迁移文件存在"""
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "005_standard_recipes.py"
        assert migration_path.exists(), "alembic/versions/005_standard_recipes.py 应该存在"

    def test_create_standard_recipes_table(self, migration_file):
        """测试创建标准化配方表"""
        assert "create_table" in migration_file, "应该有创建表操作"
        assert "'standard_recipes'" in migration_file, "应该创建 standard_recipes 表"

    def test_foreign_key_to_recipe(self, migration_file):
        """测试关联菜谱的外键"""
        assert "recipe_id" in migration_file, "应该有 recipe_id 字段"
        assert "ForeignKeyConstraint" in migration_file, "应该有外键约束"

    def test_foreign_key_to_enterprise(self, migration_file):
        """测试关联企业的外键"""
        assert "enterprise_id" in migration_file, "应该有 enterprise_id 字段"


class TestStandardizeAPI:
    """测试标准化 API"""

    @pytest.fixture
    def standardize_api_file(self) -> str:
        """读取 app/api/v1/standardize.py"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "standardize.py"
        if api_path.exists():
            with open(api_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_standardize_api_file_exists(self):
        """测试标准化 API 文件存在"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "standardize.py"
        assert api_path.exists(), "app/api/v1/standardize.py 应该存在"

    def test_generate_endpoint(self, standardize_api_file):
        """测试生成标准化配方端点"""
        assert "router.post" in standardize_api_file, "应该有 POST 端点"
        assert "/generate" in standardize_api_file or "/standardize" in standardize_api_file, "应该有生成端点"

    def test_permission_check(self, standardize_api_file):
        """测试企业权限检查"""
        assert "admin" in standardize_api_file or "enterprise" in standardize_api_file, "应该有企业权限检查"
        assert "role" in standardize_api_file, "应该有角色检查"


class TestIntegration:
    """测试集成"""

    @pytest.fixture
    def routes_file(self) -> str:
        """读取 app/api/routes.py"""
        routes_path = Path(__file__).parent.parent / "app" / "api" / "routes.py"
        if routes_path.exists():
            with open(routes_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_standardize_router_registered(self, routes_file):
        """测试标准化路由已注册"""
        assert "standardize" in routes_file, "应该导入 standardize 模块"
        assert 'prefix="/standardize"' in routes_file or "prefix='/standardize'" in routes_file, "应该注册标准化路由"

    @pytest.fixture
    def models_init_file(self) -> str:
        """读取 app/models/__init__.py"""
        init_path = Path(__file__).parent.parent / "app" / "models" / "__init__.py"
        if init_path.exists():
            with open(init_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_standard_recipe_model_exported(self, models_init_file):
        """测试标准化配方模型已导出"""
        assert "StandardRecipe" in models_init_file, "应该导出 StandardRecipe 模型"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
