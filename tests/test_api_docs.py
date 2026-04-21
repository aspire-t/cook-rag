"""
测试 API 文档 (Task #29)

Sprint 9
TDD: 验证 OpenAPI Schema 和文档完整性
"""

import pytest
from pathlib import Path


class TestAPISchemas:
    """测试 API Schema 定义"""

    @pytest.fixture
    def schemas_file(self) -> str:
        """读取 app/api/schemas.py"""
        schemas_path = Path(__file__).parent.parent / "app" / "api" / "schemas.py"
        if schemas_path.exists():
            with open(schemas_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_schemas_file_exists(self):
        """测试 Schema 文件存在"""
        schemas_path = Path(__file__).parent.parent / "app" / "api" / "schemas.py"
        assert schemas_path.exists(), "app/api/schemas.py 应该存在"

    def test_error_code_definitions(self, schemas_file):
        """测试错误码定义"""
        assert "ERROR_CODE_DESCRIPTIONS" in schemas_file, "应该有错误码说明字典"
        assert "1001" in schemas_file, "应该有认证错误码 1001"
        assert "4001" in schemas_file, "应该有菜谱错误码 4001"
        assert "5001" in schemas_file, "应该有举报错误码 5001"

    def test_search_api_schemas(self, schemas_file):
        """测试搜索 API Schema"""
        assert "class SearchRequest" in schemas_file, "应该有 SearchRequest"
        assert "class SearchResponse" in schemas_file, "应该有 SearchResponse"
        assert "query" in schemas_file, "应该有 query 字段"
        assert "results" in schemas_file, "应该有 results 字段"

    def test_recommend_api_schemas(self, schemas_file):
        """测试推荐 API Schema"""
        assert "class RecommendRequest" in schemas_file, "应该有 RecommendRequest"
        assert "class RecommendResponse" in schemas_file, "应该有 RecommendResponse"

    def test_recipe_detail_schemas(self, schemas_file):
        """测试菜谱详情 API Schema"""
        assert "class RecipeDetailResponse" in schemas_file, "应该有 RecipeDetailResponse"
        assert "class IngredientItem" in schemas_file, "应该有 IngredientItem"
        assert "class StepItem" in schemas_file, "应该有 StepItem"

    def test_favorite_api_schemas(self, schemas_file):
        """测试收藏 API Schema"""
        assert "class FavoriteRequest" in schemas_file, "应该有 FavoriteRequest"
        assert "class FavoritesResponse" in schemas_file, "应该有 FavoritesResponse"

    def test_search_history_schemas(self, schemas_file):
        """测试搜索历史 API Schema"""
        assert "class SearchHistoryItem" in schemas_file, "应该有 SearchHistoryItem"
        assert "class SearchHistoryResponse" in schemas_file, "应该有 SearchHistoryResponse"

    def test_upload_api_schemas(self, schemas_file):
        """测试上传 API Schema"""
        assert "class UploadRecipeRequest" in schemas_file, "应该有 UploadRecipeRequest"
        assert "class UploadRecipeResponse" in schemas_file, "应该有 UploadRecipeResponse"
        assert "markdown_content" in schemas_file, "应该有 markdown_content 字段"
        assert "audit_status" in schemas_file, "应该有 audit_status 字段"

    def test_report_api_schemas(self, schemas_file):
        """测试举报 API Schema"""
        assert "class ReportRecipeRequest" in schemas_file, "应该有 ReportRecipeRequest"
        assert "class ReportRecipeResponse" in schemas_file, "应该有 ReportRecipeResponse"
        assert "reason" in schemas_file, "应该有 reason 字段"

    def test_example_values(self, schemas_file):
        """测试示例值配置"""
        assert "json_schema_extra" in schemas_file, "应该有 json_schema_extra 配置"
        assert "example" in schemas_file, "应该有 example 示例"

    def test_field_descriptions(self, schemas_file):
        """测试字段描述"""
        assert "Field(" in schemas_file, "应该使用 Field 定义字段"
        assert "description=" in schemas_file, "应该有字段描述"


class TestOpenAPIIntegration:
    """测试 OpenAPI 集成"""

    @pytest.fixture
    def main_file(self) -> str:
        """读取 app/main.py"""
        main_path = Path(__file__).parent.parent / "app" / "main.py"
        if main_path.exists():
            with open(main_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_fastapi_app_configured(self, main_file):
        """测试 FastAPI 应用配置"""
        assert "FastAPI(" in main_file, "应该创建 FastAPI 应用"
        assert "title=" in main_file, "应该配置 API 标题"
        assert "description=" in main_file, "应该配置 API 描述"
        assert "version=" in main_file, "应该配置 API 版本"

    def test_docs_endpoints(self, main_file):
        """测试文档端点"""
        # FastAPI 自动生成 /docs 和 /redoc
        assert "FastAPI" in main_file, "应该使用 FastAPI"


class TestAPIDocumentation:
    """测试 API 文档完整性"""

    @pytest.fixture
    def schemas_file(self) -> str:
        """读取 app/api/schemas.py"""
        schemas_path = Path(__file__).parent.parent / "app" / "api" / "schemas.py"
        if schemas_path.exists():
            with open(schemas_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_all_endpoints_documented(self, schemas_file):
        """测试所有端点都有文档"""
        # 检查主要 API 模块都有 Schema
        assert "Search" in schemas_file, "应该有搜索 API 文档"
        assert "Recommend" in schemas_file, "应该有推荐 API 文档"
        assert "Recipe" in schemas_file, "应该有菜谱 API 文档"
        assert "Favorite" in schemas_file, "应该有收藏 API 文档"
        assert "Upload" in schemas_file, "应该有上传 API 文档"
        assert "Report" in schemas_file, "应该有举报 API 文档"

    def test_request_response_pairs(self, schemas_file):
        """测试请求/响应对"""
        # 每个 API 应该有 Request 和 Response
        assert "SearchRequest" in schemas_file and "SearchResponse" in schemas_file, "搜索 API 应该有请求和响应"
        assert "RecommendRequest" in schemas_file and "RecommendResponse" in schemas_file, "推荐 API 应该有请求和响应"
        assert "UploadRecipeRequest" in schemas_file and "UploadRecipeResponse" in schemas_file, "上传 API 应该有请求和响应"
        assert "ReportRecipeRequest" in schemas_file and "ReportRecipeResponse" in schemas_file, "举报 API 应该有请求和响应"


class TestGrafanaDashboard:
    """测试 Grafana 仪表盘配置"""

    @pytest.fixture
    def dashboard_json_file(self) -> str:
        """读取 monitoring/grafana-dashboard.json"""
        dashboard_path = Path(__file__).parent.parent / "monitoring" / "grafana-dashboard.json"
        if dashboard_path.exists():
            with open(dashboard_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    @pytest.fixture
    def dashboard_md_file(self) -> str:
        """读取 monitoring/grafana-dashboard.md"""
        dashboard_path = Path(__file__).parent.parent / "monitoring" / "grafana-dashboard.md"
        if dashboard_path.exists():
            with open(dashboard_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_dashboard_json_exists(self):
        """测试仪表盘 JSON 文件存在"""
        dashboard_path = Path(__file__).parent.parent / "monitoring" / "grafana-dashboard.json"
        assert dashboard_path.exists(), "monitoring/grafana-dashboard.json 应该存在"

    def test_dashboard_md_exists(self):
        """测试仪表盘文档存在"""
        dashboard_path = Path(__file__).parent.parent / "monitoring" / "grafana-dashboard.md"
        assert dashboard_path.exists(), "monitoring/grafana-dashboard.md 应该存在"

    def test_dashboard_panels(self, dashboard_json_file):
        """测试仪表盘面板"""
        assert "QPS" in dashboard_json_file or "queries" in dashboard_json_file.lower(), "应该有 QPS 面板"
        assert "P99" in dashboard_json_file or "latency" in dashboard_json_file.lower(), "应该有延迟面板"
        assert "cache" in dashboard_json_file.lower(), "应该有缓存面板"

    def test_dashboard_documentation(self, dashboard_md_file):
        """测试仪表盘文档"""
        assert "Grafana" in dashboard_md_file, "应该是 Grafana 文档"
        assert "Prometheus" in dashboard_md_file, "应该配置 Prometheus 数据源"
        assert "Panel" in dashboard_md_file or "面板" in dashboard_md_file, "应该有面板说明"

    def test_alert_rules(self, dashboard_md_file):
        """测试告警规则"""
        assert "alert" in dashboard_md_file.lower() or "告警" in dashboard_md_file, "应该有告警规则"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
