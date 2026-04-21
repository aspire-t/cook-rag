"""JWT Token 工具 - 颁发、验证、刷新."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt import PyJWTError

from app.core.config import settings


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    """
    创建 Access Token.

    Args:
        subject: 用户 ID (sub)
        expires_delta: 过期时间增量，默认 2 小时
        extra_claims: 额外声明

    Returns:
        JWT Token 字符串
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "iss": settings.APP_NAME,
        "type": "access",
        "jti": str(uuid.uuid4()),
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    创建 Refresh Token.

    Args:
        subject: 用户 ID (sub)
        expires_delta: 过期时间增量，默认 7 天

    Returns:
        JWT Token 字符串
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "iss": settings.APP_NAME,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """
    验证 Token 并返回 Payload.

    Args:
        token: JWT Token 字符串

    Returns:
        Payload dict，如果验证失败返回 None
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_iss": True},
        )
        return payload
    except PyJWTError:
        return None


def decode_token(token: str) -> Optional[dict]:
    """解码 Token（不验证签发者）."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except PyJWTError:
        return None


def get_token_type(payload: dict) -> str:
    """获取 Token 类型."""
    return payload.get("type", "unknown")


def get_subject(payload: dict) -> str:
    """获取用户 ID."""
    return payload.get("sub", "")


def get_jti(payload: dict) -> str:
    """获取 Token 唯一标识."""
    return payload.get("jti", "")


def is_access_token(payload: dict) -> bool:
    """是否为 Access Token."""
    return get_token_type(payload) == "access"


def is_refresh_token(payload: dict) -> bool:
    """是否为 Refresh Token."""
    return get_token_type(payload) == "refresh"
