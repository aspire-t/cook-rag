"""用户收藏管理 API."""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func as sa_func

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.favorite import Favorite
from app.models.recipe import Recipe
from app.api.schemas import APIResponse

router = APIRouter()


class FavoriteRequest(BaseModel):
    recipe_id: str


class FavoriteItem(BaseModel):
    recipe_id: str
    recipe_name: str
    cuisine: Optional[str] = None
    difficulty: Optional[str] = None
    favorited_at: datetime


class FavoritesResponse(BaseModel):
    total: int
    favorites: List[FavoriteItem]


@router.post("/favorites", response_model=APIResponse)
async def add_favorite(
    request: FavoriteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    收藏菜谱.

    如果已存在收藏，返回成功（幂等）。
    """
    try:
        # 检查菜谱是否存在
        recipe_result = await db.execute(
            select(Recipe).where(Recipe.id == request.recipe_id)
        )
        recipe = recipe_result.scalar_one_or_none()

        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")

        # 检查是否已收藏
        existing = await db.execute(
            select(Favorite).where(
                Favorite.user_id == str(current_user.id),
                Favorite.recipe_id == request.recipe_id,
            )
        )

        if existing.scalar_one_or_none():
            return APIResponse(message="已收藏")

        # 创建收藏
        favorite = Favorite(
            user_id=str(current_user.id),
            recipe_id=request.recipe_id,
        )
        db.add(favorite)

        # 更新菜谱收藏数
        recipe.favorites_count = (recipe.favorites_count or 0) + 1

        await db.commit()

        return APIResponse(message="收藏成功")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"收藏失败：{str(e)}")


@router.delete("/favorites/{recipe_id}", response_model=APIResponse)
async def remove_favorite(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取消收藏菜谱."""
    try:
        # 删除收藏
        result = await db.execute(
            delete(Favorite).where(
                Favorite.user_id == str(current_user.id),
                Favorite.recipe_id == recipe_id,
            )
        )

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="未找到收藏记录")

        # 更新菜谱收藏数
        recipe_result = await db.execute(
            select(Recipe).where(Recipe.id == recipe_id)
        )
        recipe = recipe_result.scalar_one_or_none()

        if recipe:
            recipe.favorites_count = max(0, (recipe.favorites_count or 1) - 1)

        await db.commit()

        return APIResponse(message="取消收藏成功")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"取消收藏失败：{str(e)}")


@router.get("/favorites", response_model=FavoritesResponse)
async def list_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户收藏列表."""
    try:
        offset = (page - 1) * page_size

        # 查询收藏
        result = await db.execute(
            select(Favorite, Recipe.name, Recipe.cuisine, Recipe.difficulty)
            .join(Recipe, Favorite.recipe_id == Recipe.id)
            .where(Favorite.user_id == str(current_user.id))
            .order_by(Favorite.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        rows = result.all()

        # 查询总数
        count_result = await db.execute(
            select(sa_func.count(Favorite.id))
            .where(Favorite.user_id == str(current_user.id))
        )
        total = count_result.scalar() or 0

        favorites = [
            FavoriteItem(
                recipe_id=row[0].recipe_id,
                recipe_name=row[1],
                cuisine=row[2],
                difficulty=row[3],
                favorited_at=row[0].created_at,
            )
            for row in rows
        ]

        return FavoritesResponse(total=total, favorites=favorites)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取收藏列表失败：{str(e)}")
