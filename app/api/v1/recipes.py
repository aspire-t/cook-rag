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
    views_count: int = 0
    rating: Optional[float] = None


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
                name=ing.ingredient_name,
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

        recipe.views_count = (recipe.views_count or 0) + 1
        await db.commit()

        return RecipeDetailResponse(
            id=recipe.id,
            name=recipe.name,
            description=recipe.description,
            cuisine=recipe.cuisine,
            difficulty=recipe.difficulty,
            tags=recipe.tags or [],
            prep_time=recipe.prep_time,
            cook_time=recipe.cook_time,
            ingredients=ingredients,
            steps=steps,
            favorites_count=recipe.favorites_count or 0,
            views_count=recipe.views_count or 0,
            rating=recipe.rating,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取菜谱详情失败：{str(e)}")
