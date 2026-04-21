"""
测试全局异常处理 (Task #25)

Sprint 8
TDD: 测试异常处理器和错误码体系
"""

import pytest
from pathlib import Path


class TestExceptionClasses:
    """测试异常类"""

    @pytest.fixture
    def exceptions_file(self) -> str:
        """读取 app/core/exceptions.py"""
        exceptions_path = Path(__file__).parent.parent / "app" / "core" / "exceptions.py"
        if exceptions_path.exists():
            with open(exceptions_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_exceptions_file_exists(self):
        """测试异常处理文件存在"""
        exceptions_path = Path(__file__).parent.parent / "app" / "core" / "exceptions.py"
        assert exceptions_path.exists(), "app/core/exceptions.py 应该存在"

    def test_app_exception_base_class(self, exceptions_file):
        """测试 AppException 基类"""
        assert "class AppException" in exceptions_file, "应该有 AppException 基类"
        assert "error_code" in exceptions_file, "应该有 error_code 属性"
        assert "message" in exceptions_file, "应该有 message 属性"
        assert "status_code" in exceptions_file, "应该有 status_code 属性"

    def test_authentication_exception(self, exceptions_file):
        """测试认证异常类"""
        assert "class AuthenticationException" in exceptions_file, "应该有 AuthenticationException"
        assert "ERROR_AUTH_INVALID_TOKEN" in exceptions_file or "1001" in exceptions_file, "应该有无效 Token 错误码"
        assert "ERROR_AUTH_TOKEN_EXPIRED" in exceptions_file or "1002" in exceptions_file, "应该有 Token 过期错误码"

    def test_permission_denied_exception(self, exceptions_file):
        """测试权限异常类"""
        assert "class PermissionDeniedException" in exceptions_file, "应该有 PermissionDeniedException"
        assert "ERROR_AUTH_PERMISSION_DENIED" in exceptions_file or "1006" in exceptions_file, "应该有权限不足错误码"

    def test_not_found_exception(self, exceptions_file):
        """测试 404 异常类"""
        assert "class NotFoundException" in exceptions_file, "应该有 NotFoundException"
        assert "ERROR_NOT_FOUND" in exceptions_file or "2003" in exceptions_file, "应该有资源不存在错误码"

    def test_rate_limit_exception(self, exceptions_file):
        """测试限流异常类"""
        assert "class RateLimitException" in exceptions_file, "应该有 RateLimitException"
        assert "ERROR_RATE_LIMIT_EXCEEDED" in exceptions_file or "2005" in exceptions_file, "应该有限流错误码"

    def test_recipe_exception(self, exceptions_file):
        """测试菜谱业务异常类"""
        assert "class RecipeException" in exceptions_file, "应该有 RecipeException"
        assert "ERROR_RECIPE_NOT_FOUND" in exceptions_file or "4001" in exceptions_file, "应该有菜谱不存在错误码"

    def test_report_exception(self, exceptions_file):
        """测试举报业务异常类"""
        assert "class ReportException" in exceptions_file, "应该有 ReportException"
        assert "ERROR_REPORT_ALREADY_SUBMITTED" in exceptions_file or "5001" in exceptions_file, "应该有重复举报错误码"


class TestExceptionHandler:
    """测试异常处理器"""

    @pytest.fixture
    def main_file(self) -> str:
        """读取 app/main.py"""
        main_path = Path(__file__).parent.parent / "app" / "main.py"
        if main_path.exists():
            with open(main_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_app_exception_handler_registered(self, main_file):
        """测试 AppException 处理器已注册"""
        assert "add_exception_handler" in main_file, "应该注册异常处理器"
        assert "AppException" in main_file, "应该处理 AppException"

    def test_validation_exception_handler(self, main_file):
        """测试验证异常处理器"""
        assert "RequestValidationError" in main_file or "validation_exception_handler" in main_file, "应该处理验证异常"

    def test_http_exception_handler(self, main_file):
        """测试 HTTP 异常处理器"""
        assert "HTTPException" in main_file or "http_exception_handler" in main_file, "应该处理 HTTP 异常"

    def test_global_exception_handler(self, main_file):
        """测试全局异常处理器"""
        assert "global_exception_handler" in main_file, "应该有全局异常处理器"
        assert "Exception" in main_file, "应该处理所有未捕获异常"


class TestErrorCodeSystem:
    """测试错误码体系"""

    @pytest.fixture
    def exceptions_file(self) -> str:
        """读取 app/core/exceptions.py"""
        exceptions_path = Path(__file__).parent.parent / "app" / "core" / "exceptions.py"
        if exceptions_path.exists():
            with open(exceptions_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_error_code_ranges(self, exceptions_file):
        """测试错误码分段"""
        # 1xxx: 认证相关
        assert "ERROR_AUTH" in exceptions_file, "应该有认证错误码前缀"
        # 2xxx: 通用/系统
        assert "ERROR_INTERNAL" in exceptions_file or "ERROR_BAD_REQUEST" in exceptions_file, "应该有通用错误码"
        # 3xxx: 搜索/RAG
        assert "ERROR_SEARCH" in exceptions_file or "ERROR_RAG" in exceptions_file, "应该有搜索/RAG 错误码"
        # 4xxx: 菜谱/UGC
        assert "ERROR_RECIPE" in exceptions_file, "应该有菜谱错误码"
        # 5xxx: 举报/审核
        assert "ERROR_REPORT" in exceptions_file, "应该有举报错误码"

    def test_error_message_mapping(self, exceptions_file):
        """测试错误消息映射"""
        assert "ERROR_MESSAGES" in exceptions_file, "应该有错误消息映射字典"

    def test_error_response_format(self, exceptions_file):
        """测试错误响应格式"""
        # 检查 JSONResponse 返回格式
        assert '"code"' in exceptions_file, "错误响应应该包含 code 字段"
        assert '"message"' in exceptions_file, "错误响应应该包含 message 字段"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
