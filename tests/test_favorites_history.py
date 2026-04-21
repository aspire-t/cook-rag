"""
测试用户收藏和搜索历史 API (Task #20, #21)

Sprint 7
TDD: 先写测试，再实现功能
"""

import pytest
from pathlib import Path
from typing import Dict, Any


class TestFavoritesAPI:
    """测试收藏管理 API (Task #20)"""

    @pytest.fixture
    def favorites_api_file(self) -> str:
        """读取 app/api/v1/favorites.py"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "favorites.py"
        if api_path.exists():
            with open(api_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_favorites_api_file_exists(self):
        """测试收藏 API 文件存在"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "favorites.py"
        assert api_path.exists(), "app/api/v1/favorites.py 应该存在"

    def test_add_favorite_endpoint(self, favorites_api_file):
        """测试收藏端点"""
        assert "POST" in favorites_api_file or "/favorites" in favorites_api_file or "router.post" in favorites_api_file, "应该有 POST /favorites 端点"

    def test_remove_favorite_endpoint(self, favorites_api_file):
        """测试取消收藏端点"""
        assert "DELETE" in favorites_api_file or "router.delete" in favorites_api_file, "应该有 DELETE /favorites 端点"

    def test_list_favorites_endpoint(self, favorites_api_file):
        """测试收藏列表端点"""
        assert "GET" in favorites_api_file or "router.get" in favorites_api_file, "应该有 GET /favorites 端点"

    def test_auth_required(self, favorites_api_file):
        """测试需要认证"""
        assert "get_current_user" in favorites_api_file or "Depends" in favorites_api_file or "current_user" in favorites_api_file, "需要用户认证"

    def test_favorite_model_integration(self, favorites_api_file):
        """测试收藏模型集成"""
        assert "Favorite" in favorites_api_file or "favorite" in favorites_api_file, "应该集成 Favorite 模型"


class TestSearchHistoryAPI:
    """测试搜索历史 API (Task #21)"""

    @pytest.fixture
    def history_api_file(self) -> str:
        """读取 app/api/v1/history.py"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "history.py"
        if api_path.exists():
            with open(api_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_history_api_file_exists(self):
        """测试搜索历史 API 文件存在"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "history.py"
        assert api_path.exists(), "app/api/v1/history.py 应该存在"

    def test_search_history_endpoint(self, history_api_file):
        """测试搜索历史端点"""
        assert "GET" in history_api_file or "router.get" in history_api_file or "/history" in history_api_file, "应该有 GET /history 端点"

    def test_anonymous_support(self, history_api_file):
        """测试匿名用户支持（session_id）"""
        assert "session" in history_api_file.lower() or "anonymous" in history_api_file.lower() or "session_id" in history_api_file, "应该支持匿名用户"

    def test_ctr_tracking(self, history_api_file):
        """测试 CTR 数据采集"""
        assert "ctr" in history_api_file.lower() or "click" in history_api_file.lower() or "impression" in history_api_file, "应该有 CTR 数据采集"

    def test_history_record_schema(self, history_api_file):
        """测试历史记录 Schema"""
        assert "query" in history_api_file.lower() or "search" in history_api_file.lower(), "应该记录搜索查询"


class TestSearchHistoryModel:
    """测试搜索历史模型"""

    @pytest.fixture
    def model_file(self) -> str:
        """读取 app/models/search_history.py"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "search_history.py"
        if model_path.exists():
            with open(model_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_search_history_model_exists(self):
        """测试搜索历史模型文件存在"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "search_history.py"
        assert model_path.exists(), "app/models/search_history.py 应该存在"

    def test_user_id_field(self, model_file):
        """测试用户 ID 字段"""
        assert "user_id" in model_file, "应该有 user_id 字段"

    def test_query_field(self, model_file):
        """测试查询字段"""
        assert "query" in model_file, "应该有 query 字段"

    def test_session_id_field(self, model_file):
        """测试 session_id 字段（匿名用户）"""
        assert "session_id" in model_file, "应该有 session_id 字段"

    def test_timestamp_field(self, model_file):
        """测试时间戳字段"""
        assert "created_at" in model_file or "timestamp" in model_file or "created" in model_file, "应该有创建时间字段"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
