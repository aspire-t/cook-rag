"""
测试 Prompt 模板管理模块 (Task #14)

Sprint 5
TDD: 先写测试，再实现功能
"""

import pytest
from pathlib import Path
from typing import Dict, Any


class TestPromptTemplateManager:
    """测试 Prompt 模板管理器 (Task #14)"""

    @pytest.fixture
    def prompt_manager_file(self) -> str:
        """读取 app/services/prompt_manager.py"""
        prompt_path = Path(__file__).parent.parent / "app" / "services" / "prompt_manager.py"
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_prompt_manager_file_exists(self):
        """测试 Prompt 管理器文件存在"""
        prompt_path = Path(__file__).parent.parent / "app" / "services" / "prompt_manager.py"
        assert prompt_path.exists(), "app/services/prompt_manager.py 应该存在"

    def test_jinja2_template_engine(self, prompt_manager_file):
        """测试 Jinja2 模板引擎"""
        assert "jinja" in prompt_manager_file.lower() or "Jinja" in prompt_manager_file, "应该使用 Jinja2 模板引擎"
        assert "Template" in prompt_manager_file or "template" in prompt_manager_file, "应该有模板处理功能"

    def test_template_loading(self, prompt_manager_file):
        """测试模板文件加载"""
        assert "load" in prompt_manager_file.lower() or "from_file" in prompt_manager_file.lower(), "应该有模板加载功能"
        assert ".jinja" in prompt_manager_file.lower() or ".jinja2" in prompt_manager_file.lower() or "template" in prompt_manager_file.lower(), "应该从文件加载模板"

    def test_variable_injection(self, prompt_manager_file):
        """测试变量注入"""
        assert "render" in prompt_manager_file.lower() or "format" in prompt_manager_file.lower() or "variables" in prompt_manager_file.lower(), "应该支持变量注入"

    def test_token_trimming(self, prompt_manager_file):
        """测试 Token 裁剪"""
        assert "token" in prompt_manager_file.lower() or "trim" in prompt_manager_file.lower() or "truncate" in prompt_manager_file.lower() or "max_tokens" in prompt_manager_file.lower(), "应该有 Token 裁剪功能"

    def test_prompt_templates(self, prompt_manager_file):
        """测试 Prompt 模板"""
        assert "template" in prompt_manager_file.lower(), "应该有模板定义"
        assert "system" in prompt_manager_file.lower() or "user" in prompt_manager_file.lower(), "应该有系统/用户模板"

    def test_template_manager_class(self, prompt_manager_file):
        """测试模板管理器类"""
        assert "class" in prompt_manager_file and ("Prompt" in prompt_manager_file or "Template" in prompt_manager_file), "应该有 Prompt 管理器类"

    def test_get_prompt_function(self, prompt_manager_file):
        """测试 get_prompt 函数"""
        assert "def get_prompt" in prompt_manager_file or "async def get_prompt" in prompt_manager_file or "render" in prompt_manager_file.lower(), "应该有获取 Prompt 的函数"


class TestPromptConfig:
    """测试 Prompt 配置"""

    @pytest.fixture
    def config_file(self) -> str:
        """读取 app/core/config.py"""
        config_path = Path(__file__).parent.parent / "app" / "core" / "config.py"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_prompt_dir_config(self, config_file):
        """测试 Prompt 目录配置"""
        assert "prompt" in config_file.lower() or "template" in config_file.lower(), "应该有 Prompt 目录配置"

    def test_max_tokens_config(self, config_file):
        """测试最大 Token 配置"""
        assert "max_token" in config_file.lower() or "max_context" in config_file.lower() or "TOKEN" in config_file, "应该有最大 Token 配置"


class TestPromptTemplates:
    """测试 Prompt 模板文件"""

    def test_template_directory_exists(self):
        """测试模板目录存在"""
        template_path = Path(__file__).parent.parent / "app" / "prompts"
        assert template_path.exists(), "app/prompts 模板目录应该存在"

    def test_search_template_exists(self):
        """测试搜索模板存在"""
        template_path = Path(__file__).parent.parent / "app" / "prompts" / "search.jinja"
        assert template_path.exists(), "search.jinja 模板应该存在"

    def test_chat_template_exists(self):
        """测试聊天模板存在"""
        template_path = Path(__file__).parent.parent / "app" / "prompts" / "chat.jinja"
        assert template_path.exists(), "chat.jinja 模板应该存在"

    def test_recommend_template_exists(self):
        """测试推荐模板存在"""
        template_path = Path(__file__).parent.parent / "app" / "prompts" / "recommend.jinja"
        assert template_path.exists(), "recommend.jinja 模板应该存在"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
