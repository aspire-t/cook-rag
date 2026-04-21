"""
测试 Prometheus 监控指标 (Task #26)

Sprint 8
TDD: 测试指标定义和中间件
"""

import pytest
from pathlib import Path


class TestMetricsModule:
    """测试监控指标模块"""

    @pytest.fixture
    def metrics_file(self) -> str:
        """读取 app/core/metrics.py"""
        metrics_path = Path(__file__).parent.parent / "app" / "core" / "metrics.py"
        if metrics_path.exists():
            with open(metrics_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_metrics_file_exists(self):
        """测试指标文件存在"""
        metrics_path = Path(__file__).parent.parent / "app" / "core" / "metrics.py"
        assert metrics_path.exists(), "app/core/metrics.py 应该存在"

    def test_http_request_metrics(self, metrics_file):
        """测试 HTTP 请求指标"""
        assert "http_requests_total" in metrics_file, "应该有 HTTP 请求总数指标"
        assert "http_request_duration_seconds" in metrics_file, "应该有 HTTP 请求延迟指标"
        assert "http_requests_in_progress" in metrics_file, "应该有并发请求数指标"
        assert "http_request_errors_total" in metrics_file, "应该有 HTTP 错误指标"

    def test_cache_metrics(self, metrics_file):
        """测试缓存指标"""
        assert "cache_hits_total" in metrics_file, "应该有缓存命中指标"
        assert "cache_misses_total" in metrics_file, "应该有缓存未命中指标"
        assert "cache_hit_ratio" in metrics_file, "应该有缓存命中率指标"

    def test_rag_metrics(self, metrics_file):
        """测试 RAG 搜索指标"""
        assert "rag_search_duration_seconds" in metrics_file, "应该有 RAG 搜索延迟指标"
        assert "rag_results_count" in metrics_file, "应该有 RAG 结果数量指标"

    def test_llm_metrics(self, metrics_file):
        """测试 LLM 指标"""
        assert "llm_requests_total" in metrics_file, "应该有 LLM 请求指标"
        assert "llm_tokens_total" in metrics_file, "应该有 LLM Token 消耗指标"
        assert "llm_duration_seconds" in metrics_file, "应该有 LLM 延迟指标"

    def test_business_metrics(self, metrics_file):
        """测试业务指标"""
        assert "recipe_uploads_total" in metrics_file, "应该有菜谱上传指标"
        assert "recipe_reports_total" in metrics_file, "应该有菜谱举报指标"
        assert "search_queries_total" in metrics_file, "应该有搜索查询指标"


class TestMetricsMiddleware:
    """测试 Prometheus 中间件"""

    @pytest.fixture
    def metrics_file(self) -> str:
        """读取 app/core/metrics.py"""
        metrics_path = Path(__file__).parent.parent / "app" / "core" / "metrics.py"
        if metrics_path.exists():
            with open(metrics_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_middleware_exists(self, metrics_file):
        """测试中间件存在"""
        assert "prometheus_middleware" in metrics_file, "应该有 Prometheus 中间件"

    def test_middleware_records_metrics(self, metrics_file):
        """测试中间件记录指标"""
        assert "record_http_request" in metrics_file, "中间件应该记录 HTTP 请求"
        assert "start_time" in metrics_file, "中间件应该计算延迟"
        assert "status_code" in metrics_file, "中间件应该记录状态码"

    def test_middleware_handles_errors(self, metrics_file):
        """测试中间件错误处理"""
        assert "record_http_error" in metrics_file, "中间件应该记录错误"
        assert "error_type" in metrics_file, "中间件应该记录错误类型"

    def test_endpoint_simplification(self, metrics_file):
        """测试端点简化"""
        assert "_simplify_endpoint" in metrics_file, "应该有端点简化函数"
        assert "UUID" in metrics_file or "id}" in metrics_file, "应该简化 UUID 参数"


class TestMetricsEndpoint:
    """测试指标端点"""

    @pytest.fixture
    def metrics_file(self) -> str:
        """读取 app/core/metrics.py"""
        metrics_path = Path(__file__).parent.parent / "app" / "core" / "metrics.py"
        if metrics_path.exists():
            with open(metrics_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_metrics_endpoint_exists(self, metrics_file):
        """测试指标端点存在"""
        assert "metrics_handler" in metrics_file, "应该有指标端点处理器"
        assert "/metrics" in metrics_file, "应该有 /metrics 端点"

    def test_prometheus_format(self, metrics_file):
        """测试 Prometheus 格式输出"""
        assert "generate_latest" in metrics_file, "应该生成 Prometheus 格式数据"
        assert "CONTENT_TYPE_LATEST" in metrics_file, "应该设置正确的 Content-Type"
        assert "PlainTextResponse" in metrics_file, "应该返回纯文本响应"


class TestMetricRecordingFunctions:
    """测试指标记录函数"""

    @pytest.fixture
    def metrics_file(self) -> str:
        """读取 app/core/metrics.py"""
        metrics_path = Path(__file__).parent.parent / "app" / "core" / "metrics.py"
        if metrics_path.exists():
            with open(metrics_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_record_http_request(self, metrics_file):
        """测试 HTTP 请求记录函数"""
        assert "def record_http_request" in metrics_file, "应该有 record_http_request 函数"

    def test_record_cache(self, metrics_file):
        """测试缓存记录函数"""
        assert "def record_cache_hit" in metrics_file, "应该有 record_cache_hit 函数"
        assert "def record_cache_miss" in metrics_file, "应该有 record_cache_miss 函数"

    def test_record_rag_search(self, metrics_file):
        """测试 RAG 搜索记录函数"""
        assert "def record_rag_search" in metrics_file, "应该有 record_rag_search 函数"

    def test_record_llm_request(self, metrics_file):
        """测试 LLM 请求记录函数"""
        assert "def record_llm_request" in metrics_file, "应该有 record_llm_request 函数"
        assert "prompt_tokens" in metrics_file, "应该记录 prompt Token"
        assert "completion_tokens" in metrics_file, "应该记录 completion Token"


class TestMainIntegration:
    """测试主应用集成"""

    @pytest.fixture
    def main_file(self) -> str:
        """读取 app/main.py"""
        main_path = Path(__file__).parent.parent / "app" / "main.py"
        if main_path.exists():
            with open(main_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_middleware_registered(self, main_file):
        """测试中间件注册"""
        # 检查是否导入了中间件
        assert "metrics" in main_file.lower() or "prometheus" in main_file.lower(), "应该导入 metrics 模块"

    def test_metrics_endpoint_registered(self, main_file):
        """测试指标端点注册"""
        assert "/metrics" in main_file or "metrics_handler" in main_file, "应该注册 /metrics 端点"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
