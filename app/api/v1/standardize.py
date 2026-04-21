"""B 端标准化配方生成 API."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.enterprise import EnterpriseUser
from app.services.standardize_service import StandardizeService
from app.api.schemas import APIResponse

router = APIRouter()


# ============ Schema 定义 ============

class GenerateStandardRecipeRequest(BaseModel):
    """生成标准化配方请求."""
    recipe_id: str = Field(..., description="菜谱 ID")
    enterprise_id: str = Field(..., description="企业 ID")


class SOPIngredient(BaseModel):
    """SOP 配料项."""
    ingredient: str
    spec: Optional[str] = None
    amount_g: float
    tolerance_g: float = 5.0
    note: Optional[str] = None


class SOPProcedure(BaseModel):
    """SOP 步骤项."""
    step_num: int
    title: str
    duration_min: int
    operation: str
    critical_control_point: str
    quality_check: str


class SOPContent(BaseModel):
    """SOP 内容."""
    ingredients_table: list[SOPIngredient] = []
    procedures: list[SOPProcedure] = []


class CostIngredient(BaseModel):
    """成本核算食材项."""
    ingredient: str
    unit_price_kg: float
    amount_g: float
    cost: float


class CostCalculation(BaseModel):
    """成本核算."""
    ingredients: list[CostIngredient] = []
    total_cost: float
    suggested_price: float
    gross_margin: float


class NutritionInfo(BaseModel):
    """营养成分表."""
    per_100g: dict = {}


class AllergenInfo(BaseModel):
    """过敏原信息."""
    contains: list[str] = []
    may_contain: list[str] = []


class ShelfLife(BaseModel):
    """保质期信息."""
    days: int
    storage_temp: str
    frozen_days: Optional[int] = None
    frozen_temp: Optional[str] = None


class StandardRecipeResponse(BaseModel):
    """标准化配方响应."""
    id: str
    recipe_id: str
    enterprise_id: str
    version: int
    is_latest: bool

    # SOP
    sop: Optional[SOPContent] = None

    # 成本核算
    total_cost: Optional[float] = None
    suggested_price: Optional[float] = None
    gross_margin: Optional[float] = None

    # 营养信息
    nutrition_info: Optional[NutritionInfo] = None

    # 过敏原
    allergen_info: Optional[AllergenInfo] = None

    # 保质期
    shelf_life_days: Optional[int] = None
    storage_temperature: Optional[str] = None

    created_at: datetime


# ============ API 端点 ============

@router.post("/generate", response_model=APIResponse)
async def generate_standard_recipe(
    request: GenerateStandardRecipeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    生成标准化配方.

    将家庭菜谱转化为可工业化生产的标准化配方，包括：
    - 标准操作流程 (SOP)
    - 成本核算
    - 营养成分表
    - 过敏原信息
    - 保质期与储存要求

    仅企业成员可使用。
    """
    try:
        # 初始化服务
        service = StandardizeService(db)

        # 检查企业权限
        has_permission = await service.check_enterprise_permission(
            enterprise_id=request.enterprise_id,
            user_id=str(current_user.id),
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="无权访问该企业")

        # 检查角色权限（仅管理员和厨师可生成标准化配方）
        user_enterprise_result = await db.execute(
            select(EnterpriseUser).where(
                EnterpriseUser.enterprise_id == request.enterprise_id,
                EnterpriseUser.user_id == current_user.id,
                EnterpriseUser.is_active,
            )
        )
        user_enterprise = user_enterprise_result.scalar_one_or_none()
        if user_enterprise and user_enterprise.role not in ["admin", "chef"]:
            raise HTTPException(status_code=403, detail="仅管理员和厨师可生成标准化配方")

        # 生成标准化配方
        standard_recipe = await service.generate_standard_recipe(
            recipe_id=request.recipe_id,
            enterprise_id=request.enterprise_id,
            created_by=str(current_user.id),
        )

        return APIResponse(
            message="标准化配方生成成功",
            data={"standard_recipe_id": str(standard_recipe.id)},
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"生成失败：{str(e)}")


@router.get("/recipes/{recipe_id}/standard", response_model=Optional[StandardRecipeResponse])
async def get_standard_recipe(
    recipe_id: str,
    enterprise_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取菜谱的标准化配方.

    返回最新版本。
    """
    try:
        service = StandardizeService(db)

        # 检查企业权限
        has_permission = await service.check_enterprise_permission(
            enterprise_id=enterprise_id,
            user_id=str(current_user.id),
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="无权访问该企业")

        # 获取标准化配方
        standard_recipe = await service.get_latest_standard_recipe(
            recipe_id=recipe_id,
            enterprise_id=enterprise_id,
        )

        if not standard_recipe:
            return None

        # 解析 JSON 字段
        import json
        sop = json.loads(standard_recipe.sop_content) if standard_recipe.sop_content else None
        nutrition = json.loads(standard_recipe.nutrition_info) if standard_recipe.nutrition_info else None
        allergen = json.loads(standard_recipe.allergen_info) if standard_recipe.allergen_info else None

        return StandardRecipeResponse(
            id=str(standard_recipe.id),
            recipe_id=standard_recipe.recipe_id,
            enterprise_id=standard_recipe.enterprise_id,
            version=standard_recipe.version,
            is_latest=standard_recipe.is_latest,
            sop=sop,
            total_cost=standard_recipe.total_cost,
            suggested_price=standard_recipe.suggested_price,
            gross_margin=standard_recipe.gross_margin,
            nutrition_info=nutrition,
            allergen_info=allergen,
            shelf_life_days=standard_recipe.shelf_life_days,
            storage_temperature=standard_recipe.storage_temperature,
            created_at=standard_recipe.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败：{str(e)}")
