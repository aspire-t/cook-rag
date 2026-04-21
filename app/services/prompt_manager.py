"""Prompt 模板管理模块 - Jinja2 模板引擎，变量注入，Token 裁剪."""

from pathlib import Path
from typing import Dict, Any, Optional, List
from jinja2 import Environment, FileSystemLoader, Template
import tiktoken

from app.core.config import settings


class PromptTemplateManager:
    """
    Prompt 模板管理器.

    功能：
    - Jinja2 模板引擎
    - 从文件加载模板
    - 变量注入
    - Token 裁剪（固定优先级）
    """

    # Token 裁剪优先级（从高到低）
    TRIM_PRIORITY = [
        "examples",      # 1. 裁剪示例
        "context",       # 2. 裁剪上下文
        "history",       # 3. 裁剪历史
        "description",   # 4. 裁剪描述
    ]

    def __init__(
        self,
        template_dir: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ):
        """
        初始化 Prompt 管理器.

        Args:
            template_dir: 模板目录路径
            max_tokens: 最大 Token 数
        """
        self.template_dir = Path(template_dir) if template_dir else Path(__file__).parent.parent / "prompts"
        self.max_tokens = max_tokens or settings.MAX_CONTEXT_TOKENS

        # 初始化 Jinja2 环境
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            auto_reload=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # 缓存已加载的模板
        self._templates: Dict[str, Template] = {}

        # 初始化 tokenizer（使用 GPT-4 的编码器近似估算）
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None

    def _count_tokens(self, text: str) -> int:
        """
        计算 Token 数量.

        Args:
            text: 文本

        Returns:
            Token 数量
        """
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # 简单估算：中文按字符数/4，英文按单词数
            return len(text) // 4

    def get_template(self, name: str) -> Template:
        """
        获取模板.

        Args:
            name: 模板名称（不含扩展名）

        Returns:
            Jinja2 模板对象
        """
        if name not in self._templates:
            # 尝试加载 .jinja 或 .jinja2 文件
            for ext in [".jinja", ".jinja2", ""]:
                try:
                    self._templates[name] = self.env.get_template(f"{name}{ext}")
                    break
                except Exception:
                    continue

        return self._templates.get(name)

    def render(
        self,
        template_name: str,
        variables: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        渲染 Prompt 模板.

        Args:
            template_name: 模板名称
            variables: 模板变量
            max_tokens: 最大 Token 数（覆盖默认值）

        Returns:
            渲染后的 Prompt
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"模板不存在：{template_name}")

        # 渲染模板
        variables = variables or {}
        prompt = template.render(**variables)

        # Token 裁剪
        target_tokens = max_tokens or self.max_tokens
        if self._count_tokens(prompt) > target_tokens:
            prompt = self._trim_prompt(prompt, variables, target_tokens)

        return prompt

    def _trim_prompt(
        self,
        prompt: str,
        variables: Dict[str, Any],
        target_tokens: int,
    ) -> str:
        """
        裁剪 Prompt.

        按优先级裁剪：examples > context > history > description

        Args:
            prompt: 原始 Prompt
            variables: 模板变量
            target_tokens: 目标 Token 数

        Returns:
            裁剪后的 Prompt
        """
        # 尝试按优先级裁剪各个部分
        for field in self.TRIM_PRIORITY:
            if field in variables:
                value = variables[field]
                if isinstance(value, list) and len(value) > 0:
                    # 裁剪列表（保留 50%）
                    new_length = max(1, len(value) // 2)
                    variables[field] = value[:new_length]

                    # 重新渲染
                    template = self.get_template("system")
                    if template:
                        prompt = template.render(**variables)

                    # 检查是否满足要求
                    if self._count_tokens(prompt) <= target_tokens:
                        return prompt

        # 如果还是太长，简单截断
        tokens = prompt.split()
        while len(tokens) > 0 and self._count_tokens(" ".join(tokens)) > target_tokens:
            tokens = tokens[:-10]

        return " ".join(tokens)

    def get_prompt(
        self,
        template_name: str,
        system_template: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        获取完整的 Prompt（system + user）.

        Args:
            template_name: 用户模板名称
            system_template: 系统模板名称（默认为 system）
            variables: 模板变量

        Returns:
            {"system": str, "user": str}
        """
        system_name = system_template or "system"
        variables = variables or {}

        # 渲染系统 Prompt
        system_prompt = self.render(system_name, variables)

        # 渲染用户 Prompt
        user_prompt = self.render(template_name, variables)

        return {
            "system": system_prompt,
            "user": user_prompt,
        }

    def clear_cache(self):
        """清除模板缓存."""
        self._templates.clear()


# 全局单例
_prompt_manager: Optional[PromptTemplateManager] = None


def get_prompt_manager() -> PromptTemplateManager:
    """获取 Prompt 管理器实例."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptTemplateManager()
    return _prompt_manager


def render_prompt(
    template_name: str,
    variables: Optional[Dict[str, Any]] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    渲染 Prompt 便捷函数.

    Args:
        template_name: 模板名称
        variables: 模板变量
        max_tokens: 最大 Token 数

    Returns:
        渲染后的 Prompt
    """
    manager = get_prompt_manager()
    return manager.render(template_name, variables, max_tokens)


def get_chat_prompt(
    context: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    question: Optional[str] = None,
) -> Dict[str, str]:
    """
    获取聊天 Prompt.

    Args:
        context: RAG 上下文（搜索结果）
        history: 对话历史
        question: 用户问题

    Returns:
        {"system": str, "user": str}
    """
    manager = get_prompt_manager()
    return manager.get_prompt(
        "chat",
        variables={
            "context": context or "",
            "history": history or [],
            "question": question or "",
        },
    )


def get_search_prompt(
    query: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    获取搜索 Prompt.

    Args:
        query: 搜索查询
        filters: 过滤条件

    Returns:
        {"system": str, "user": str}
    """
    manager = get_prompt_manager()
    return manager.get_prompt(
        "search",
        variables={
            "query": query or "",
            "filters": filters or {},
        },
    )


def get_recommend_prompt(
    user_prefs: Optional[Dict[str, Any]] = None,
    context: Optional[str] = None,
) -> Dict[str, str]:
    """
    获取推荐 Prompt.

    Args:
        user_prefs: 用户偏好
        context: 上下文

    Returns:
        {"system": str, "user": str}
    """
    manager = get_prompt_manager()
    return manager.get_prompt(
        "recommend",
        variables={
            "user_prefs": user_prefs or {},
            "context": context or "",
        },
    )
