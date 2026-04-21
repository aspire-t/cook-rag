"""通义千问 LLM API 集成 - 调用阿里云百炼 Qwen-Plus API."""

import asyncio
from typing import AsyncGenerator, Optional, Dict, Any, List
from dataclasses import dataclass
import dashscope
from dashscope import Generation
from dashscope.api_entities.dashscope_response import GenerationResponse

from app.core.config import settings


@dataclass
class LLMResponse:
    """LLM 响应."""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str


class LLMService:
    """
    通义千问 LLM 服务.

    功能：
    - 调用阿里云百炼 Qwen-Plus API
    - 流式输出（C 端）
    - 超时重试（30s，3 次）
    """

    # 配置
    DEFAULT_MODEL = "qwen-plus"
    MAX_TOKENS = 2048
    TIMEOUT_SECONDS = 30
    MAX_RETRIES = 3

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        初始化 LLM 服务.

        Args:
            api_key: DashScope API Key
            model: 模型名称
        """
        self.api_key = api_key or settings.DASHSCOPE_API_KEY
        self.model = model or settings.LLM_MODEL or self.DEFAULT_MODEL

        # 配置 API Key
        if self.api_key:
            dashscope.api_key = self.api_key

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> LLMResponse:
        """
        生成响应（非流式）.

        Args:
            messages: 消息列表 [{"role": "system"|"user"|"assistant", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大 Token 数
            stream: 是否流式输出

        Returns:
            LLM 响应
        """
        max_tokens = max_tokens or self.MAX_TOKENS

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await asyncio.wait_for(
                    self._call_api(messages, temperature, max_tokens, stream=False),
                    timeout=self.TIMEOUT_SECONDS,
                )
                return response
            except asyncio.TimeoutError:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))  # 指数退避
            except Exception as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise LLMError(f"LLM 调用失败：{e}")
                await asyncio.sleep(1 * (attempt + 1))

        raise LLMError("达到最大重试次数")

    async def _call_api(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> LLMResponse:
        """调用 API."""
        loop = asyncio.get_event_loop()

        def sync_call():
            response = Generation.call(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
            )
            return response

        response = await loop.run_in_executor(None, sync_call)

        if not response or not response.output:
            raise LLMError("API 返回空响应")

        return LLMResponse(
            content=response.output.get("text", ""),
            model=response.model or self.model,
            usage=dict(response.usage) if response.usage else {},
            finish_reason=response.output.get("finish_reason", "stop"),
        )

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        生成流式响应.

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 Token 数

        Yields:
            响应文本片段
        """
        max_tokens = max_tokens or self.MAX_TOKENS

        for attempt in range(self.MAX_RETRIES):
            try:
                async for chunk in await asyncio.wait_for(
                    self._call_api_stream(messages, temperature, max_tokens),
                    timeout=self.TIMEOUT_SECONDS * 2,  # 流式允许更长时间
                ):
                    yield chunk
                return
            except asyncio.TimeoutError:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))
            except Exception as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise LLMError(f"LLM 流式调用失败：{e}")
                await asyncio.sleep(1 * (attempt + 1))

    async def _call_api_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """调用流式 API."""
        loop = asyncio.get_event_loop()

        def sync_stream_call():
            responses = Generation.call(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                result_format="message",
            )
            for response in responses:
                yield response

        # 使用异步生成器包装同步生成器
        for response in sync_stream_call():
            if response and response.output:
                content = response.output.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content:
                    yield content

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """
        聊天接口.

        Args:
            system_prompt: 系统 Prompt
            user_prompt: 用户 Prompt
            history: 对话历史
            stream: 是否流式输出

        Returns:
            LLM 响应或流式生成器
        """
        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]

        # 添加历史
        if history:
            messages.extend(history)

        # 添加用户消息
        messages.append({"role": "user", "content": user_prompt})

        if stream:
            return self.generate_stream(messages)
        else:
            return await self.generate(messages)


class LLMError(Exception):
    """LLM 调用异常."""
    pass


# 全局服务实例
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """获取 LLM 服务实例."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


async def generate_response(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> LLMResponse:
    """
    生成响应便捷函数.

    Args:
        messages: 消息列表
        temperature: 温度参数
        max_tokens: 最大 Token 数

    Returns:
        LLM 响应
    """
    service = get_llm_service()
    return await service.generate(messages, temperature, max_tokens)


async def generate_chat_response(
    system_prompt: str,
    user_prompt: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> LLMResponse:
    """
    聊天响应便捷函数.

    Args:
        system_prompt: 系统 Prompt
        user_prompt: 用户 Prompt
        history: 对话历史

    Returns:
        LLM 响应
    """
    service = get_llm_service()
    return await service.chat(system_prompt, user_prompt, history, stream=False)


async def stream_chat_response(
    system_prompt: str,
    user_prompt: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> AsyncGenerator[str, None]:
    """
    流式聊天响应便捷函数.

    Args:
        system_prompt: 系统 Prompt
        user_prompt: 用户 Prompt
        history: 对话历史

    Yields:
        响应文本片段
    """
    service = get_llm_service()
    async for chunk in await service.chat(system_prompt, user_prompt, history, stream=True):
        yield chunk
