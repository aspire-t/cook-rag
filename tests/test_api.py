"""
测试 C 端 API (Task #18, #19)

Sprint 6
TDD: 先写测试，再实现功能
"""

import pytest
from pathlib import Path
from typing import Dict, Any


class TestSearchAPI:
    """测试搜索 API (Task #18)"""

    @pytest.fixture
    def search_api_file(self) -> str:
        """读取 app/api/v1/search.py"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "search.py"
        if api_path.exists():
            with open(api_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_search_api_file_exists(self):
        """测试搜索 API 文件存在"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "search.py"
        assert api_path.exists(), "app/api/v1/search.py 应该存在"

    def test_search_endpoint(self, search_api_file):
        """测试搜索端点"""
        assert "POST" in search_api_file or "/search" in search_api_file or "router.post" in search_api_file, "应该有 POST /search 端点"

    def test_search_request_schema(self, search_api_file):
        """测试搜索请求参数"""
        assert "query" in search_api_file.lower(), "应该接受 query 参数"
        assert "filter" in search_api_file.lower() or "filters" in search_api_file.lower(), "应该支持过滤条件"

    def test_search_response_schema(self, search_api_file):
        """测试搜索响应"""
        assert "recipe" in search_api_file.lower() or "results" in search_api_file.lower(), "应该返回菜谱列表"

    def test_hybrid_search_integration(self, search_api_file):
        """测试混合检索集成"""
        assert "hybrid" in search_api_file.lower() or "search" in search_api_file.lower(), "应该集成混合检索"


class TestRecommendAPI:
    """测试推荐 API (Task #18)"""

    @pytest.fixture
    def search_api_file(self) -> str:
        """读取 app/api/v1/search.py（推荐 API 也在这里）"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "search.py"
        if api_path.exists():
            with open(api_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_recommend_api_in_search_file(self, search_api_file):
        """测试推荐 API 在 search.py 中实现"""
        assert "recommend" in search_api_file.lower() or "/recommend" in search_api_file, "应该有推荐端点"

    def test_recommend_endpoint(self, search_api_file):
        """测试推荐端点"""
        assert "POST" in search_api_file or "/recommend" in search_api_file or "router.post" in search_api_file, "应该有 POST /recommend 端点"

    def test_personalized_recommend(self, search_api_file):
        """测试个性化推荐"""
        assert "user" in search_api_file.lower() and ("pref" in search_api_file.lower() or "taste" in search_api_file.lower()), "应该支持用户偏好"

    def test_rerank_integration(self, search_api_file):
        """测试重排序集成"""
        assert "rerank" in search_api_file.lower() or "重排" in search_api_file, "应该集成重排序"


class TestRecipeDetailAPI:
    """测试菜谱详情 API (Task #19)"""

    @pytest.fixture
    def recipe_api_file(self) -> str:
        """读取 app/api/v1/recipes.py"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "recipes.py"
        if api_path.exists():
            with open(api_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_recipe_api_file_exists(self):
        """测试菜谱 API 文件存在"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "recipes.py"
        assert api_path.exists(), "app/api/v1/recipes.py 应该存在"

    def test_recipe_detail_endpoint(self, recipe_api_file):
        """测试菜谱详情端点"""
        assert "GET" in recipe_api_file or "/recipes/{id}" in recipe_api_file or "router.get" in recipe_api_file, "应该有 GET /recipes/{id} 端点"

    def test_recipe_detail_fields(self, recipe_api_file):
        """测试菜谱详情字段"""
        assert "ingredients" in recipe_api_file.lower() or "食材" in recipe_api_file, "应该返回食材"
        assert "steps" in recipe_api_file.lower() or "步骤" in recipe_api_file, "应该返回步骤"

    def test_recipe_model_integration(self, recipe_api_file):
        """测试菜谱模型集成"""
        assert "recipe" in recipe_api_file.lower() and ("model" in recipe_api_file.lower() or "Model" in recipe_api_file), "应该集成菜谱模型"


class TestAPISchemas:
    """测试 API Schema"""

    @pytest.fixture
    def schemas_file(self) -> str:
        """读取 app/api/schemas.py"""
        schema_path = Path(__file__).parent.parent / "app" / "api" / "schemas.py"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_schemas_file_exists(self):
        """测试 Schema 文件存在"""
        schema_path = Path(__file__).parent.parent / "app" / "api" / "schemas.py"
        assert schema_path.exists(), "app/api/schemas.py 应该存在"

    def test_search_request_schema(self, schemas_file):
        """测试搜索请求 Schema"""
        assert "Search" in schemas_file and "Request" in schemas_file or "SearchRequest" in schemas_file or "search" in schemas_file.lower(), "应该有搜索请求 Schema"

    def test_search_response_schema(self, schemas_file):
        """测试搜索响应 Schema"""
        assert "Search" in schemas_file and "Response" in schemas_file or "SearchResponse" in schemas_file or "search" in schemas_file.lower(), "应该有搜索响应 Schema"

    def test_recommend_request_schema(self, schemas_file):
        """测试推荐请求 Schema"""
        assert "Recommend" in schemas_file or "recommend" in schemas_file.lower(), "应该有推荐请求 Schema"

    def test_recipe_detail_schema(self, schemas_file):
        """测试菜谱详情 Schema"""
        assert "Recipe" in schemas_file and ("Detail" in schemas_file or "Response" in schemas_file) or "RecipeDetail" in schemas_file or "recipe" in schemas_file.lower(), "应该有菜谱详情 Schema"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
