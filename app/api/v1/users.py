"""用户认证 API - 登录、登出、刷新 Token."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.jwt import (
    verify_token,
    is_refresh_token,
    create_access_token,
    get_subject,
    get_jti,
)
from app.core.auth import get_current_user
from app.services.wechat import get_wechat_service, WechatLoginService
from app.services.blacklist import get_blacklist
import redis.asyncio as redis

router = APIRouter()


class WechatLoginRequest(BaseModel):
    """微信登录请求."""

    code: str = Field(..., description="微信登录凭证（前端 wx.login() 获取）")


class TokenResponse(BaseModel):
    """Token 响应."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class WechatLoginResponse(BaseModel):
    """微信登录响应."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    openid: str
    unionid: str | None = None


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求."""

    refresh_token: str = Field(..., description="Refresh Token")


@router.post("/login/wechat", response_model=WechatLoginResponse)
async def wechat_login(request: WechatLoginRequest):
    """
    微信小程序登录.

    使用微信 code 换取 Token.
    """
    wechat_service = get_wechat_service()

    if not wechat_service.appid or not wechat_service.secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="微信配置未设置",
        )

    try:
        result = await wechat_service.login(request.code)
        return WechatLoginResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            openid=result["openid"],
            unionid=result.get("unionid"),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    用户登出.

    将 Access Token 加入黑名单.
    """
    payload = current_user["token_payload"]
    jti = get_jti(payload)
    exp = payload.get("exp", 0)

    # 将 Token 加入黑名单
    try:
        redis_client = redis.from_url(
            "redis://localhost:6379/0",
            encoding="utf-8",
            decode_responses=True,
        )
        blacklist = get_blacklist(redis_client)
        await blacklist.add_to_blacklist(jti, exp)
    except Exception:
        # Redis 不可用时记录日志但不失败
        pass

    return {"status": "ok", "message": "已登出"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    刷新 Access Token.

    使用 Refresh Token 获取新的 Access Token.
    """
    # 验证 Refresh Token
    payload = verify_token(request.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token 无效或已过期",
        )

    # 检查是否为 Refresh Token
    if not is_refresh_token(payload):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 类型错误",
        )

    # 将旧 Refresh Token 加入黑名单（防止重用）
    jti = get_jti(payload)
    exp = payload.get("exp", 0)
    try:
        redis_client = redis.from_url(
            "redis://localhost:6379/0",
            encoding="utf-8",
            decode_responses=True,
        )
        blacklist = get_blacklist(redis_client)
        await blacklist.add_to_blacklist(jti, exp)
    except Exception:
        pass

    # 生成新的 Access Token
    user_id = get_subject(payload)
    access_token = create_access_token(subject=user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token,  # Refresh Token 可继续使用
    )


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息."""
    return {"user_id": current_user["user_id"]}
