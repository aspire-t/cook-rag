"""限流中间件 - 基于 Redis ZSet 的滑动窗口算法。

支持按 API 类型配置不同的限流阈值。
"""

import time
from typing import Optional, Dict
from dataclasses import dataclass
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import redis.asyncio as redis


@dataclass
class RateLimitConfig:
    """限流配置."""
    limit: int  # 窗口内最大请求数
    window_seconds: int  # 窗口大小（秒）


class SlidingWindowRateLimiter:
    """滑动窗口限流器（Redis ZSet 实现）."""

    # 默认配置：100 次/分钟
    DEFAULT_CONFIG = RateLimitConfig(limit=100, window_seconds=60)

    # API 类型配置
    API_CONFIGS: Dict[str, RateLimitConfig] = {
        "search": RateLimitConfig(limit=30, window_seconds=60),  # 搜索 API：30 次/分钟
        "llm": RateLimitConfig(limit=10, window_seconds=60),  # LLM API：10 次/分钟
        "auth": RateLimitConfig(limit=5, window_seconds=60),  # 认证 API：5 次/分钟
        "upload": RateLimitConfig(limit=20, window_seconds=60),  # 上传 API：20 次/分钟
    }

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

    def get_config_for_path(self, path: str) -> RateLimitConfig:
        """
        根据路径获取限流配置.

        Args:
            path: API 路径

        Returns:
            对应的限流配置
        """
        # 根据路径匹配 API 类型
        if "/search" in path or "/recommend" in path:
            return self.API_CONFIGS.get("search", self.DEFAULT_CONFIG)
        elif "/llm" in path or "/chat" in path or "/generate" in path:
            return self.API_CONFIGS.get("llm", self.DEFAULT_CONFIG)
        elif "/login" in path or "/auth" in path or "/refresh" in path:
            return self.API_CONFIGS.get("auth", self.DEFAULT_CONFIG)
        elif "/upload" in path or "/recipes" in path:
            return self.API_CONFIGS.get("upload", self.DEFAULT_CONFIG)
        else:
            return self.DEFAULT_CONFIG

    async def is_allowed(
        self,
        identifier: str,
        path: Optional[str] = None,
    ) -> tuple[bool, RateLimitConfig]:
        """
        检查请求是否允许.

        Args:
            identifier: 请求标识（用户 ID 或 IP）
            path: API 路径（用于选择配置）

        Returns:
            (是否允许，使用的配置)
        """
        # 根据路径选择配置
        config = self.get_config_for_path(path) if path else self.DEFAULT_CONFIG

        key = f"{self.prefix}:{identifier}:{config.limit}:{config.window_seconds}"
        now = time.time()
        window_start = now - config.window_seconds

        # 使用 Pipeline 保证原子性
        pipe = self.redis.pipeline()

        # 移除窗口外的请求
        pipe.zremrangebyscore(key, 0, window_start)

        # 添加当前请求
        pipe.zadd(key, {str(now): now})

        # 统计窗口内请求数
        pipe.zcard(key)

        # 设置过期时间
        pipe.expire(key, config.window_seconds)

        # 执行
        results = await pipe.execute()
        current_count = results[2]

        return (current_count <= config.limit, config)


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

        # 检查限流（传入路径以选择配置）
        try:
            allowed, config = await limiter.is_allowed(identifier, request.url.path)
        except Exception:
            # Redis 不可用时放行（开发环境）
            return await call_next(request)
        finally:
            await redis_client.close()

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "请求过于频繁，请稍后再试",
                    "retry_after": config.window_seconds,
                    "limit": config.limit,
                },
                headers={"Retry-After": str(config.window_seconds)},
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
