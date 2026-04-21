"""Redis 缓存层服务 - 搜索缓存、LLM 响应缓存、用户画像缓存."""

import json
import hashlib
from typing import Any, Optional, Dict
from datetime import timedelta
import redis.asyncio as redis

from app.core.config import settings


class CacheService:
    """
    Redis 缓存服务.

    提供三类缓存：
    - 搜索缓存：1h TTL，缓存搜索结果
    - LLM 响应缓存：24h TTL，缓存 LLM 生成内容
    - 用户画像缓存：30m TTL，缓存用户偏好
    """

    # TTL 配置（秒）
    SEARCH_TTL = 3600  # 1h
    LLM_RESPONSE_TTL = 86400  # 24h
    USER_PROFILE_TTL = 1800  # 30m

    # 键前缀
    SEARCH_PREFIX = "cookrag:cache:search"
    LLM_PREFIX = "cookrag:cache:llm"
    USER_PREFIX = "cookrag:cache:user"

    def __init__(self, redis_url: Optional[str] = None):
        """
        初始化缓存服务.

        Args:
            redis_url: Redis URL
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[redis.Redis] = None

    @property
    async def redis(self) -> redis.Redis:
        """获取 Redis 连接（懒加载）."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    def _generate_key(self, prefix: str, *args: Any) -> str:
        """
        生成缓存键.

        Args:
            prefix: 键前缀
            *args: 键参数

        Returns:
            缓存键字符串
        """
        # 将参数转换为 JSON 字符串并生成 MD5 哈希
        key_data = json.dumps(args, sort_keys=True)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}:{key_hash}"

    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存.

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在返回 None
        """
        redis_client = await self.redis
        value = await redis_client.get(key)
        if value is None:
            return None

        # 尝试反序列化 JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        设置缓存.

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 使用默认值

        Returns:
            True 如果成功
        """
        redis_client = await self.redis

        # 序列化值
        if isinstance(value, (dict, list)):
            serialized = json.dumps(value, ensure_ascii=False)
        else:
            serialized = str(value)

        # 设置过期时间
        if ttl:
            await redis_client.setex(key, ttl, serialized)
        else:
            await redis_client.set(key, serialized)

        return True

    async def delete(self, key: str) -> bool:
        """
        删除缓存.

        Args:
            key: 缓存键

        Returns:
            True 如果成功
        """
        redis_client = await self.redis
        await redis_client.delete(key)
        return True

    async def get_search(self, query: str, filters: Optional[Dict] = None) -> Optional[Any]:
        """
        获取搜索缓存.

        Args:
            query: 搜索查询
            filters: 过滤条件

        Returns:
            缓存的搜索结果
        """
        key = self._generate_key(self.SEARCH_PREFIX, query, filters)
        return await self.get(key)

    async def set_search(
        self,
        query: str,
        filters: Optional[Dict],
        results: Any,
    ) -> bool:
        """
        设置搜索缓存.

        Args:
            query: 搜索查询
            filters: 过滤条件
            results: 搜索结果

        Returns:
            True 如果成功
        """
        key = self._generate_key(self.SEARCH_PREFIX, query, filters)
        return await self.set(key, results, ttl=self.SEARCH_TTL)

    async def get_llm_response(self, prompt_key: str, context_hash: str) -> Optional[Any]:
        """
        获取 LLM 响应缓存.

        Args:
            prompt_key: Prompt 模板键
            context_hash: 上下文哈希

        Returns:
            缓存的 LLM 响应
        """
        key = self._generate_key(self.LLM_PREFIX, prompt_key, context_hash)
        return await self.get(key)

    async def set_llm_response(
        self,
        prompt_key: str,
        context_hash: str,
        response: Any,
    ) -> bool:
        """
        设置 LLM 响应缓存.

        Args:
            prompt_key: Prompt 模板键
            context_hash: 上下文哈希
            response: LLM 响应

        Returns:
            True 如果成功
        """
        key = self._generate_key(self.LLM_PREFIX, prompt_key, context_hash)
        return await self.set(key, response, ttl=self.LLM_RESPONSE_TTL)

    async def get_user_profile(self, user_id: str) -> Optional[Any]:
        """
        获取用户画像缓存.

        Args:
            user_id: 用户 ID

        Returns:
            缓存的用户画像
        """
        key = self._generate_key(self.USER_PREFIX, user_id)
        return await self.get(key)

    async def set_user_profile(self, user_id: str, profile: Dict) -> bool:
        """
        设置用户画像缓存.

        Args:
            user_id: 用户 ID
            profile: 用户画像数据

        Returns:
            True 如果成功
        """
        key = self._generate_key(self.USER_PREFIX, user_id)
        return await self.set(key, profile, ttl=self.USER_PROFILE_TTL)

    async def invalidate_user_profile(self, user_id: str) -> bool:
        """
        失效用户画像缓存.

        Args:
            user_id: 用户 ID

        Returns:
            True 如果成功
        """
        key = self._generate_key(self.USER_PREFIX, user_id)
        return await self.delete(key)

    async def close(self):
        """关闭 Redis 连接."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# 全局服务实例
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """获取缓存服务实例."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


async def cache_search_results(
    query: str,
    filters: Optional[Dict] = None,
    results: Optional[Any] = None,
) -> Optional[Any]:
    """
    缓存搜索结果（get/set 统一接口）.

    Args:
        query: 搜索查询
        filters: 过滤条件
        results: 搜索结果（提供则 set，否则 get）

    Returns:
        缓存的搜索结果
    """
    service = get_cache_service()

    if results is not None:
        return await service.set_search(query, filters, results)
    else:
        return await service.get_search(query, filters)


async def cache_llm_response(
    prompt_key: str,
    context_hash: str,
    response: Optional[Any] = None,
) -> Optional[Any]:
    """
    缓存 LLM 响应（get/set 统一接口）.

    Args:
        prompt_key: Prompt 模板键
        context_hash: 上下文哈希
        response: LLM 响应（提供则 set，否则 get）

    Returns:
        缓存的 LLM 响应
    """
    service = get_cache_service()

    if response is not None:
        return await service.set_llm_response(prompt_key, context_hash, response)
    else:
        return await service.get_llm_response(prompt_key, context_hash)


async def cache_user_profile(
    user_id: str,
    profile: Optional[Dict] = None,
) -> Optional[Dict]:
    """
    缓存用户画像（get/set 统一接口）.

    Args:
        user_id: 用户 ID
        profile: 用户画像数据（提供则 set，否则 get）

    Returns:
        缓存的用户画像
    """
    service = get_cache_service()

    if profile is not None:
        await service.set_user_profile(user_id, profile)
        return profile
    else:
        return await service.get_user_profile(user_id)
