"""
菜谱 API
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from app.services.recipe_service import RecipeService


router = APIRouter()


class RecipeResponse(BaseModel):
    id: str
    name: str
    description: str
    cuisine: str
    difficulty: str
    prep_time: int
    cook_time: int


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(recipe_id: str):
    """获取菜谱详情"""
    service = RecipeService()
    recipe = await service.get_recipe(recipe_id)

    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return recipe


@router.get("/")
async def list_recipes(
    cuisine: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """获取菜谱列表"""
    service = RecipeService()
    recipes = await service.list_recipes(
        cuisine=cuisine,
        difficulty=difficulty,
        limit=limit,
        offset=offset,
    )
    return {"total": len(recipes), "recipes": recipes}


@router.post("/")
async def create_recipe(recipe_data: dict):
    """创建菜谱（UGC）"""
    service = RecipeService()
    recipe = await service.create_recipe(recipe_data)
    return recipe