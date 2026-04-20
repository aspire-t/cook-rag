"""
用户 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter()


class UserProfile(BaseModel):
    id: str
    nickname: str
    taste_prefs: dict
    dietary_restrictions: list


@router.get("/me", response_model=UserProfile)
async def get_current_user():
    """获取当前用户信息"""
    # TODO: 实现认证
    return {
        "id": "user_001",
        "nickname": "测试用户",
        "taste_prefs": {"spicy": 0.8},
        "dietary_restrictions": [],
    }


@router.post("/profile")
async def update_profile(profile: dict):
    """更新用户画像"""
    return {"status": "ok"}