"""微信小程序登录服务."""

import httpx
from typing import Optional
from pydantic import BaseModel

from app.core.config import settings
from app.core.jwt import create_access_token, create_refresh_token


class WechatCodeResponse(BaseModel):
    """微信 code 换 token 响应."""

    openid: str
    session_key: str
    unionid: Optional[str] = None


class WechatLoginService:
    """微信登录服务."""

    # 微信 API 基础 URL
    JS_CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"

    def __init__(
        self,
        appid: Optional[str] = None,
        secret: Optional[str] = None,
    ):
        """
        初始化微信登录服务.

        Args:
            appid: 小程序 AppID
            secret: 小程序 Secret
        """
        self.appid = appid or settings.WECHAT_APPID
        self.secret = secret or settings.WECHAT_SECRET

    async def code_to_session(self, code: str) -> Optional[WechatCodeResponse]:
        """
        用 code 换取 session.

        Args:
            code: 微信登录凭证（前端 wx.login() 获取）

        Returns:
            WechatCodeResponse 或 None（如果失败）
        """
        params = {
            "appid": self.appid,
            "secret": self.secret,
            "js_code": code,
            "grant_type": settings.WECHAT_GRANT_TYPE,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.JS_CODE2SESSION_URL, params=params)
                data = response.json()

                # 微信返回错误
                if "errcode" in data:
                    return None

                return WechatCodeResponse(
                    openid=data.get("openid"),
                    session_key=data.get("session_key"),
                    unionid=data.get("unionid"),
                )
            except Exception:
                return None

    async def login(self, code: str) -> dict:
        """
        微信登录 - 返回 Token.

        Args:
            code: 微信登录凭证

        Returns:
            {"access_token": str, "refresh_token": str, "openid": str}

        Raises:
            ValueError: 登录失败
        """
        session = await self.code_to_session(code)
        if not session:
            raise ValueError("微信登录失败")

        # 用 openid 作为用户标识生成 Token
        access_token = create_access_token(subject=session.openid)
        refresh_token = create_refresh_token(subject=session.openid)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "openid": session.openid,
            "unionid": session.unionid,
        }


# 全局服务实例
_wechat_service: Optional[WechatLoginService] = None


def get_wechat_service() -> WechatLoginService:
    """获取微信登录服务实例."""
    global _wechat_service
    if _wechat_service is None:
        _wechat_service = WechatLoginService()
    return _wechat_service
