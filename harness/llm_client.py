"""
LLM Client - 统一的 LLM 调用接口

支持通义千问 API，提供简单的调用封装
"""

import asyncio
import json
from typing import Optional, List, Dict, Any

import httpx
from loguru import logger


class LLMClient:
    """LLM 客户端"""

    def __init__(
        self,
        base_url: str = "https://dashscope.aliyuncs.com/api/v1",
        api_key: Optional[str] = None,
        default_model: str = "qwen-plus",
    ):
        self.base_url = base_url
        self.api_key = api_key or self._get_api_key_from_env()
        self.default_model = default_model
        self.client = httpx.AsyncClient(timeout=60.0)

    def _get_api_key_from_env(self) -> str:
        """从环境变量获取 API Key"""
        import os
        return os.environ.get("DASHSCOPE_API_KEY", "")

    async def call(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        调用 LLM

        Args:
            prompt: 用户输入
            model: 模型名称
            max_tokens: 最大输出 token 数
            temperature: 温度参数
            system_prompt: 系统提示

        Returns:
            LLM 响应文本
        """
        model = model or self.default_model

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.post(
                f"{self.base_url}/services/aigc/text-generation/generation",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": {"messages": messages},
                    "parameters": {
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            if "output" in data and "choices" in data["output"]:
                return data["output"]["choices"][0]["message"]["content"]
            elif "output" in data and "text" in data["output"]:
                return data["output"]["text"]
            else:
                logger.error(f"Unexpected response format: {data}")
                return ""

        except httpx.HTTPError as e:
            logger.error(f"LLM API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    async def stream_call(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
    ):
        """流式调用 LLM"""
        # TODO: 实现流式调用
        pass

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 全局客户端实例
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取全局 LLM 客户端实例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


async def call_llm(
    prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    system_prompt: Optional[str] = None,
) -> str:
    """
    便捷的 LLM 调用函数

    Args:
        prompt: 用户输入
        model: 模型名称
        max_tokens: 最大输出 token 数
        temperature: 温度参数
        system_prompt: 系统提示

    Returns:
        LLM 响应文本
    """
    client = get_llm_client()
    return await client.call(
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system_prompt=system_prompt,
    )
