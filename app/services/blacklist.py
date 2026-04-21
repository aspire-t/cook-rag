"""Token 黑名单服务 - 使用 Redis."""

import time
from typing import Optional

import redis.asyncio as redis


class TokenBlacklist:
    """JWT 黑名单管理（Redis）."""

    def __init__(self, redis_client: redis.Redis, ttl_hours: int = 3):
        """
        初始化黑名单服务.

        Args:
            redis_client: Redis 客户端
            ttl_hours: 黑名单 TTL（小时），默认 3 小时（Access Token 2h + 缓冲 1h）
        """
        self.redis = redis_client
        self.ttl = ttl_hours * 3600

    async def add_to_blacklist(self, jti: str, exp: int) -> None:
        """
        将 Token 加入黑名单.

        Args:
            jti: Token 唯一标识
            exp: Token 过期时间（Unix 时间戳）
        """
        key = f"token:blacklist:{jti}"
        # TTL 设置为 Token 剩余有效期
        ttl = max(exp - int(time.time()), 0)
        if ttl > 0:
            await self.redis.set(key, "1", ex=ttl)

    async def is_blacklisted(self, jti: str) -> bool:
        """
        检查 Token 是否在黑名单.

        Args:
            jti: Token 唯一标识

        Returns:
            True 如果在黑名单中
        """
        return await self.redis.exists(f"token:blacklist:{jti}")

    async def remove_from_blacklist(self, jti: str) -> None:
        """
        从黑名单移除 Token.

        Args:
            jti: Token 唯一标识
        """
        key = f"token:blacklist:{jti}"
        await self.redis.delete(key)


# 全局黑名单实例（懒加载）
_blacklist: Optional[TokenBlacklist] = None


def get_blacklist(redis_client: Optional[redis.Redis] = None) -> TokenBlacklist:
    """
    获取黑名单实例.

    Args:
        redis_client: Redis 客户端，如果提供则创建新实例

    Returns:
        TokenBlacklist 实例
    """
    global _blacklist
    if redis_client:
        return TokenBlacklist(redis_client)
    if _blacklist is None:
        raise RuntimeError("Blacklist not initialized. Call with redis_client first.")
    return _blacklist
