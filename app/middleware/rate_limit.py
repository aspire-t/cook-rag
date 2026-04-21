"""限流中间件 - 基于 Redis ZSet 的滑动窗口算法."""

import time
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import redis.asyncio as redis


class SlidingWindowRateLimiter:
    """滑动窗口限流器（Redis ZSet 实现）."""

    def __init__(
        self,
        redis_client: redis.Redis,
        limit: int = 100,
        window_seconds: int = 60,
        key_prefix: str = "ratelimit",
    ):
        """
        初始化限流器.

        Args:
            redis_client: Redis 客户端
            limit: 窗口内最大请求数，默认 100 次/分钟
            window_seconds: 窗口大小（秒），默认 60 秒
            key_prefix: Redis Key 前缀
        """
        self.redis = redis_client
        self.limit = limit
        self.window = window_seconds
        self.prefix = key_prefix

    async def is_allowed(self, identifier: str) -> bool:
        """
        检查请求是否允许.

        Args:
            identifier: 请求标识（用户 ID 或 IP）

        Returns:
            True 允许请求，False 限流
        """
        key = f"{self.prefix}:{identifier}"
        now = time.time()
        window_start = now - self.window

        # 使用 Pipeline 保证原子性
        pipe = self.redis.pipeline()

        # 移除窗口外的请求
        pipe.zremrangebyscore(key, 0, window_start)

        # 添加当前请求
        pipe.zadd(key, {str(now): now})

        # 统计窗口内请求数
        pipe.zcard(key)

        # 设置过期时间
        pipe.expire(key, self.window)

        # 执行
        results = await pipe.execute()
        current_count = results[2]

        return current_count <= self.limit


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI 限流中间件."""

    def __init__(
        self,
        app,
        redis_url: str = "redis://localhost:6379/0",
        limit: int = 100,
        window_seconds: int = 60,
        exclude_paths: Optional[list] = None,
    ):
        """
        初始化中间件.

        Args:
            app: FastAPI 应用
            redis_url: Redis URL
            limit: 限流阈值
            window_seconds: 窗口大小
            exclude_paths: 不限流的路径
        """
        super().__init__(app)
        self.redis_url = redis_url
        self.limit = limit
        self.window = window_seconds
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json"]

    async def dispatch(self, request: Request, call_next):
        """处理请求."""
        # 跳过排除路径
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # 获取请求标识（优先用户 ID，其次 IP）
        identifier = self._get_identifier(request)

        # 创建限流器
        redis_client = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        limiter = SlidingWindowRateLimiter(
            redis_client,
            limit=self.limit,
            window_seconds=self.window,
        )

        # 检查限流
        try:
            allowed = await limiter.is_allowed(identifier)
        except Exception:
            # Redis 不可用时放行（开发环境）
            return await call_next(request)
        finally:
            await redis_client.close()

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "请求过于频繁，请稍后再试"},
                headers={"Retry-After": str(self.window)},
            )

        return await call_next(request)

    def _get_identifier(self, request: Request) -> str:
        """获取请求标识."""
        # 优先使用认证用户 ID
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return f"user:{user_id}"

        # 使用 IP 地址
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"


def create_rate_limit_middleware(
    redis_url: str = "redis://localhost:6379/0",
    limit: int = 100,
    window_seconds: int = 60,
):
    """
    创建限流中间件工厂函数.

    Args:
        redis_url: Redis URL
        limit: 限流阈值
        window_seconds: 窗口大小

    Returns:
        RateLimitMiddleware 类
    """
    return lambda app: RateLimitMiddleware(
        app,
        redis_url=redis_url,
        limit=limit,
        window_seconds=window_seconds,
    )
