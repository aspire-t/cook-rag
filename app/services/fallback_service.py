"""三级降级策略 - LLM API 故障 → Web Search → 规则引擎兜底."""

import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx

from app.services.llm_service import get_llm_service, LLMService, LLMError
from app.core.config import settings


@dataclass
class QueryResult:
    """查询结果."""
    content: str
    source: str  # "llm", "web_search", "rule_engine"
    confidence: float  # 置信度 0-1
    metadata: Optional[Dict[str, Any]] = None


class FallbackService:
    """
    三级降级服务.

    降级策略：
    1. LLM API（通义千问）- 主选
    2. Web Search（Bing）- 第一降级
    3. 规则引擎 - 最终兜底
    """

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        web_search_api_key: Optional[str] = None,
    ):
        """
        初始化降级服务.

        Args:
            llm_service: LLM 服务
            web_search_api_key: Bing Search API Key
        """
        self.llm_service = llm_service or get_llm_service()
        self.web_search_api_key = web_search_api_key

    async def query(
        self,
        system_prompt: str,
        user_query: str,
        context: Optional[str] = None,
        use_fallback: bool = True,
    ) -> QueryResult:
        """
        查询入口.

        Args:
            system_prompt: 系统 Prompt
            user_query: 用户查询
            context: RAG 上下文（搜索结果）
            use_fallback: 是否启用降级

        Returns:
            查询结果
        """
        if use_fallback:
            return await self._query_with_fallback(system_prompt, user_query, context)
        else:
            # 直接使用 LLM
            try:
                response = await self.llm_service.chat(system_prompt, user_query)
                return QueryResult(
                    content=response.content,
                    source="llm",
                    confidence=0.9,
                )
            except Exception as e:
                return self._rule_engine_fallback(user_query, str(e))

    async def _query_with_fallback(
        self,
        system_prompt: str,
        user_query: str,
        context: Optional[str],
    ) -> QueryResult:
        """带降级的查询."""
        # Level 1: LLM API
        try:
            # 构建完整 Prompt
            if context:
                full_prompt = f"""【参考信息】
{context}

【用户问题】
{user_query}

请根据参考信息回答问题。"""
            else:
                full_prompt = user_query

            response = await self.llm_service.chat(system_prompt, full_prompt)
            return QueryResult(
                content=response.content,
                source="llm",
                confidence=0.9,
            )
        except (LLMError, asyncio.TimeoutError) as e:
            print(f"LLM 调用失败，降级到 Web Search: {e}")

        # Level 2: Web Search
        try:
            web_results = await self._web_search(user_query)
            if web_results:
                # 使用 Web 搜索结果生成回答
                search_context = "\n".join([r["snippet"] for r in web_results[:5]])
                summary_prompt = f"""根据以下搜索结果回答问题：

搜索内容：
{search_context}

问题：{user_query}

请综合以上信息，给出简洁准确的回答。"""

                try:
                    response = await self.llm_service.chat(system_prompt, summary_prompt)
                    return QueryResult(
                        content=response.content,
                        source="web_search",
                        confidence=0.6,
                        metadata={"web_results": web_results[:3]},
                    )
                except Exception:
                    # LLM 不可用时，直接返回搜索结果
                    return QueryResult(
                        content=self._format_search_results(web_results),
                        source="web_search",
                        confidence=0.5,
                        metadata={"web_results": web_results[:3]},
                    )
        except Exception as e:
            print(f"Web Search 失败，降级到规则引擎：{e}")

        # Level 3: 规则引擎兜底
        return self._rule_engine_fallback(user_query)

    async def _web_search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Web 搜索（Bing）.

        Args:
            query: 搜索查询

        Returns:
            搜索结果列表
        """
        if not self.web_search_api_key:
            return None

        endpoint = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": self.web_search_api_key}
        params = {"q": query, "count": 5, "mkt": "zh-CN"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(endpoint, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                return data.get("webPages", {}).get("value", [])
        except Exception:
            return None

    def _format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """格式化搜索结果."""
        if not results:
            return "抱歉，未能找到相关信息。"

        lines = ["根据网络搜索结果："]
        for i, r in enumerate(results[:5], 1):
            lines.append(f"{i}. {r.get('name', '无标题')}: {r.get('snippet', '无摘要')}")

        return "\n".join(lines)

    def _rule_engine_fallback(
        self,
        query: str,
        error_msg: Optional[str] = None,
    ) -> QueryResult:
        """
        规则引擎兜底.

        基于关键词匹配和预设规则回答。

        Args:
            query: 用户查询
            error_msg: 错误信息

        Returns:
            查询结果
        """
        # 简单关键词匹配规则
        query_lower = query.lower()

        # 菜谱相关规则
        if any(kw in query_lower for kw in ["怎么做", "做法", "烹饪", "制作"]):
            return QueryResult(
                content=f"""抱歉，暂时无法获取详细的菜谱信息。

您可以尝试：
1. 提供更具体的食材名称
2. 说明您想要的菜系（如川菜、粤菜等）
3. 描述您的口味偏好

或者稍后再试，我们将为您提供更详细的烹饪指导。""",
                source="rule_engine",
                confidence=0.3,
            )

        # 食材相关规则
        if any(kw in query_lower for kw in ["食材", "材料", "配料"]):
            return QueryResult(
                content="""抱歉，暂时无法获取详细的食材信息。

一般来说，一道菜的主要食材包括：
- 主料（肉类、海鲜、蔬菜等）
- 辅料（调味料、香料等）

建议您提供具体的菜名，我可以帮您查找相关信息。""",
                source="rule_engine",
                confidence=0.3,
            )

        # 营养相关规则
        if any(kw in query_lower for kw in ["营养", "热量", "卡路里", "蛋白质"]):
            return QueryResult(
                content="""抱歉，暂时无法获取详细的营养信息。

营养成分通常包括：
- 热量（卡路里）
- 蛋白质
- 脂肪
- 碳水化合物

建议您咨询专业营养师或查阅营养数据库获取准确信息。""",
                source="rule_engine",
                confidence=0.3,
            )

        # 通用兜底
        return QueryResult(
            content=f"""抱歉，我暂时无法回答这个问题。

我可以帮您：
- 推荐菜谱
- 提供烹饪技巧
- 解答食材相关问题

请尝试换一种方式提问，或者稍后再试。""",
            source="rule_engine",
            confidence=0.2,
        )


# 全局服务实例
_fallback_service: Optional[FallbackService] = None


def get_fallback_service() -> FallbackService:
    """获取降级服务实例."""
    global _fallback_service
    if _fallback_service is None:
        _fallback_service = FallbackService()
    return _fallback_service


async def query_with_fallback(
    system_prompt: str,
    user_query: str,
    context: Optional[str] = None,
) -> QueryResult:
    """
    带降级的查询入口.

    Args:
        system_prompt: 系统 Prompt
        user_query: 用户查询
        context: RAG 上下文

    Returns:
        查询结果
    """
    service = get_fallback_service()
    return await service.query(system_prompt, user_query, context)
