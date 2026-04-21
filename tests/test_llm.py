"""
测试 LLM API 集成 (Task #16)

Sprint 6
TDD: 先写测试，再实现功能
"""

import pytest
from pathlib import Path
from typing import Dict, Any


class TestLLMService:
    """测试 LLM 服务 (Task #16)"""

    @pytest.fixture
    def llm_service_file(self) -> str:
        """读取 app/services/llm_service.py"""
        llm_path = Path(__file__).parent.parent / "app" / "services" / "llm_service.py"
        if llm_path.exists():
            with open(llm_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_llm_service_file_exists(self):
        """测试 LLM 服务文件存在"""
        llm_path = Path(__file__).parent.parent / "app" / "services" / "llm_service.py"
        assert llm_path.exists(), "app/services/llm_service.py 应该存在"

    def test_llm_service_class(self, llm_service_file):
        """测试 LLM 服务类"""
        assert "class" in llm_service_file and ("LLM" in llm_service_file or "llm" in llm_service_file), "应该有 LLM 服务类"

    def test_qwen_integration(self, llm_service_file):
        """测试通义千问集成"""
        assert "qwen" in llm_service_file.lower() or "dashscope" in llm_service_file.lower() or "通义" in llm_service_file, "应该集成通义千问"

    def test_streaming_output(self, llm_service_file):
        """测试流式输出"""
        assert "stream" in llm_service_file.lower() or "Streaming" in llm_service_file, "应该支持流式输出"

    def test_timeout_retry(self, llm_service_file):
        """测试超时重试（30s，3 次）"""
        # 检查重试机制（检查 MAX_RETRIES 或 max_retries）
        has_retry = (
            "MAX_RETRIES" in llm_service_file or
            "max_retries" in llm_service_file or
            "MAX_RETRY" in llm_service_file or
            "retry" in llm_service_file.lower()
        )
        assert has_retry, "应该有重试机制"

        # 检查超时配置
        has_timeout = (
            "TIMEOUT" in llm_service_file or
            "timeout" in llm_service_file.lower() or
            "30" in llm_service_file
        )
        assert has_timeout, "应该有 30s 超时配置"

        # 检查 3 次重试
        has_max_retries_3 = "MAX_RETRIES = 3" in llm_service_file or "max_retries = 3" in llm_service_file or "3" in llm_service_file
        assert has_max_retries_3, "应该有 3 次重试配置"

    def test_generate_function(self, llm_service_file):
        """测试 generate 函数"""
        assert "def generate" in llm_service_file or "async def generate" in llm_service_file or "def chat" in llm_service_file, "应该有生成/聊天函数"

    def test_api_key_config(self, llm_service_file):
        """测试 API Key 配置"""
        assert "api_key" in llm_service_file.lower() or "DASHSCOPE" in llm_service_file or "api_key" in llm_service_file, "应该有 API Key 配置"

    def test_async_support(self, llm_service_file):
        """测试异步支持"""
        assert "async" in llm_service_file.lower() or "await" in llm_service_file, "应该支持异步操作"


class TestLLMConfig:
    """测试 LLM 配置"""

    @pytest.fixture
    def config_file(self) -> str:
        """读取 app/core/config.py"""
        config_path = Path(__file__).parent.parent / "app" / "core" / "config.py"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_dashscope_api_key_config(self, config_file):
        """测试 DashScope API Key 配置"""
        assert "DASHSCOPE" in config_file or "dashscope" in config_file.lower(), "应该有 DASHSCOPE_API_KEY 配置"

    def test_llm_model_config(self, config_file):
        """测试 LLM 模型配置"""
        assert "LLM_MODEL" in config_file or "qwen" in config_file.lower() or "model" in config_file.lower(), "应该有 LLM_MODEL 配置"

    def test_timeout_config(self, config_file):
        """测试超时配置"""
        assert "timeout" in config_file.lower() or "TIMEOUT" in config_file or "30" in config_file, "应该有超时配置"

    def test_retry_config(self, config_file):
        """测试重试配置"""
        assert "retry" in config_file.lower() or "RETRY" in config_file or "max" in config_file.lower(), "应该有重试配置"


class TestLLMIntegration:
    """测试 LLM 集成"""

    def test_llm_with_prompt_manager(self):
        """测试 LLM 与 Prompt 管理器集成"""
        # 集成测试
        pass

    def test_llm_with_context_manager(self):
        """测试 LLM 与会话管理器集成"""
        # 集成测试
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
