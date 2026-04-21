"""认证依赖注入 - FastAPI Depends."""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.jwt import verify_token, get_subject, is_access_token, get_jti
from app.services.blacklist import get_blacklist
import redis.asyncio as redis

# HTTP Bearer Scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    获取当前认证用户.

    Args:
        credentials: HTTP Bearer 凭证

    Returns:
        用户信息 dict {"user_id": str, "token_payload": dict}

    Raises:
        HTTPException: 认证失败
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # 验证 Token
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查是否为 Access Token
    if not is_access_token(payload):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 类型错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查黑名单
    jti = get_jti(payload)
    try:
        # 懒加载 Redis 连接
        redis_client = redis.from_url(
            "redis://localhost:6379/0",
            encoding="utf-8",
            decode_responses=True,
        )
        blacklist = get_blacklist(redis_client)
        if await blacklist.is_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token 已注销",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception:
        # Redis 不可用时跳过黑名单检查（开发环境）
        pass

    user_id = get_subject(payload)
    return {"user_id": user_id, "token_payload": payload}


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """
    获取可选认证用户（不强制要求登录）.

    Args:
        credentials: HTTP Bearer 凭证

    Returns:
        用户信息 dict 或 None
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
