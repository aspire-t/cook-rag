"""菜谱 API 路由."""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.recipe import Recipe
from app.models.ingredient import RecipeIngredient
from app.models.step import RecipeStep
from app.models.recipe_image import RecipeImage
from app.services.image_url_builder import build_fallback_image_url

router = APIRouter()


class IngredientItem(BaseModel):
    name: str
    amount: Optional[str] = None
    unit: Optional[str] = None
    sequence: int = 0


class StepItem(BaseModel):
    step_no: int
    description: str
    duration_seconds: Optional[int] = None


class RecipeDetailResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    cuisine: Optional[str] = None
    difficulty: Optional[str] = None
    tags: List[str] = []
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None
    ingredients: List[IngredientItem] = []
    steps: List[StepItem] = []
    favorites_count: int = 0
    view_count: int = 0
    rating: Optional[float] = None
    cover_image: Optional[str] = None
    cover_fallback_url: Optional[str] = None
    step_images: List[dict] = []


@router.get("/{recipe_id}", response_model=RecipeDetailResponse)
async def get_recipe_detail(
    recipe_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取菜谱详情.

    返回：
    - 菜谱基本信息
    - 食材列表
    - 烹饪步骤
    """
    try:
        result = await db.execute(
            select(Recipe).where(Recipe.id == recipe_id)
        )
        recipe = result.scalar_one_or_none()

        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")

        ingredients_result = await db.execute(
            select(RecipeIngredient)
            .where(RecipeIngredient.recipe_id == recipe_id)
            .order_by(RecipeIngredient.sequence)
        )
        ingredients = [
            IngredientItem(
                name=ing.name,
                amount=str(ing.amount) if ing.amount else None,
                unit=ing.unit,
                sequence=ing.sequence,
            )
            for ing in ingredients_result.scalars().all()
        ]

        steps_result = await db.execute(
            select(RecipeStep)
            .where(RecipeStep.recipe_id == recipe_id)
            .order_by(RecipeStep.step_no)
        )
        steps = [
            StepItem(
                step_no=step.step_no,
                description=step.description,
                duration_seconds=step.duration_seconds,
            )
            for step in steps_result.scalars().all()
        ]

        recipe.view_count = (recipe.view_count or 0) + 1
        await db.commit()

        # 查询图片
        images_result = await db.execute(
            select(RecipeImage)
            .where(RecipeImage.recipe_id == recipe.id)
            .order_by(RecipeImage.step_no.nullsfirst(), RecipeImage.id)
        )
        images = images_result.scalars().all()

        cover_image = None
        cover_fallback = None
        step_images = []
        for img in images:
            fallback = build_fallback_image_url(img.source_path)
            if img.image_type == "cover":
                cover_image = img.image_url
                cover_fallback = fallback
            else:
                step_images.append({
                    "step_no": img.step_no,
                    "url": img.image_url,
                    "fallback_url": fallback,
                })
        step_images.sort(key=lambda x: x["step_no"] or 0)

        return RecipeDetailResponse(
            id=str(recipe.id),
            name=recipe.name,
            description=recipe.description,
            cuisine=recipe.cuisine,
            difficulty=recipe.difficulty,
            tags=recipe.tags or [],
            prep_time=recipe.prep_time,
            cook_time=recipe.cook_time,
            ingredients=ingredients,
            steps=steps,
            favorites_count=recipe.favorite_count or 0,
            view_count=recipe.view_count or 0,
            rating=None,
            cover_image=cover_image,
            cover_fallback_url=cover_fallback,
            step_images=step_images,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取菜谱详情失败：{str(e)}")
