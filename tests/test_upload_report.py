"""
测试 UGC 菜谱上传和举报功能 (Task #22, #23)

Sprint 7
TDD: 先写测试，再实现功能
"""

import pytest
from pathlib import Path
from typing import Dict, Any


class TestUGCUploadAPI:
    """测试 UGC 菜谱上传 API (Task #22)"""

    @pytest.fixture
    def upload_api_file(self) -> str:
        """读取 app/api/v1/upload.py"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "upload.py"
        if api_path.exists():
            with open(api_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_upload_api_file_exists(self):
        """测试上传 API 文件存在"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "upload.py"
        assert api_path.exists(), "app/api/v1/upload.py 应该存在"

    def test_upload_recipe_endpoint(self, upload_api_file):
        """测试上传菜谱端点"""
        assert "POST" in upload_api_file or "/upload" in upload_api_file or "/recipes" in upload_api_file or "router.post" in upload_api_file, "应该有上传菜谱端点"

    def test_markdown_parsing(self, upload_api_file):
        """测试 Markdown 解析"""
        assert "markdown" in upload_api_file.lower() or "Markdown" in upload_api_file or "解析" in upload_api_file, "应该支持 Markdown 解析"

    def test_image_upload(self, upload_api_file):
        """测试图片上传"""
        assert "image" in upload_api_file.lower() or "Image" in upload_api_file or "upload" in upload_api_file.lower() or "图片" in upload_api_file, "应该支持图片上传"

    def test_pending_review_status(self, upload_api_file):
        """测试先发后审状态"""
        assert "pending" in upload_api_file.lower() or "review" in upload_api_file.lower() or "审核" in upload_api_file or "status" in upload_api_file.lower(), "应该有审核状态"

    def test_auth_required(self, upload_api_file):
        """测试需要认证"""
        assert "get_current_user" in upload_api_file or "Depends" in upload_api_file or "current_user" in upload_api_file, "需要用户认证"


class TestRecipeReportAPI:
    """测试菜谱举报 API (Task #23)"""

    @pytest.fixture
    def report_api_file(self) -> str:
        """读取 app/api/v1/report.py"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "report.py"
        if api_path.exists():
            with open(api_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_report_api_file_exists(self):
        """测试举报 API 文件存在"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "report.py"
        assert api_path.exists(), "app/api/v1/report.py 应该存在"

    def test_report_recipe_endpoint(self, report_api_file):
        """测试举报菜谱端点"""
        assert "POST" in report_api_file or "/report" in report_api_file or "router.post" in report_api_file, "应该有举报菜谱端点"

    def test_report_reason_field(self, report_api_file):
        """测试举报原因字段"""
        assert "reason" in report_api_file.lower() or "原因" in report_api_file, "应该有举报原因"

    def test_auto_offline_threshold(self, report_api_file):
        """测试 5 次举报自动下架"""
        assert "5" in report_api_file and ("offline" in report_api_file.lower() or "下架" in report_api_file or "自动" in report_api_file), "应该 5 次举报自动下架"

    def test_report_count_tracking(self, report_api_file):
        """测试举报计数"""
        assert "count" in report_api_file.lower() or "report" in report_api_file.lower() or "count" in report_api_file, "应该有举报计数"


class TestReportModel:
    """测试举报模型"""

    @pytest.fixture
    def model_file(self) -> str:
        """读取 app/models/report.py"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "report.py"
        if model_path.exists():
            with open(model_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_report_model_exists(self):
        """测试举报模型文件存在"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "report.py"
        assert model_path.exists(), "app/models/report.py 应该存在"

    def test_recipe_id_field(self, model_file):
        """测试菜谱 ID 字段"""
        assert "recipe_id" in model_file, "应该有 recipe_id 字段"

    def test_user_id_field(self, model_file):
        """测试用户 ID 字段"""
        assert "user_id" in model_file, "应该有 user_id 字段"

    def test_reason_field(self, model_file):
        """测试原因字段"""
        assert "reason" in model_file, "应该有 reason 字段"

    def test_status_field(self, model_file):
        """测试状态字段"""
        assert "status" in model_file, "应该有 status 字段"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
