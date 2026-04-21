"""菜谱举报 API."""

import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.recipe import Recipe
from app.models.report import Report
from app.api.schemas import APIResponse

router = APIRouter()


# 自动下架阈值
AUTO_OFFLINE_THRESHOLD = 5


@router.post("/report", response_model=APIResponse)
async def report_recipe(
    recipe_id: str = Form(..., description="菜谱 ID"),
    reason: str = Form(..., description="举报原因"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    举报菜谱.

    功能:
    - 提交举报原因
    - 自动计数：达到 5 次举报自动下架待审核
    - 防止重复举报

    业务逻辑:
    1. 检查菜谱是否存在
    2. 检查用户是否已举报过该菜谱（防止刷举报）
    3. 创建举报记录
    4. 更新菜谱举报计数
    5. 达到阈值自动下架（audit_status=pending, is_public=False）
    """
    try:
        # 检查菜谱是否存在
        result = await db.execute(
            select(Recipe).where(Recipe.id == recipe_id)
        )
        recipe = result.scalar_one_or_none()

        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")

        # 检查是否重复举报
        existing_report = await db.execute(
            select(Report).where(
                Report.recipe_id == recipe_id,
                Report.user_id == str(current_user.id),
            )
        )
        if existing_report.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="您已举报过该菜谱，无需重复举报")

        # 创建举报记录
        report_id = str(uuid.uuid4())
        report = Report(
            id=report_id,
            recipe_id=recipe_id,
            user_id=str(current_user.id),
            reason=reason,
            status="pending",
        )
        db.add(report)

        # 更新菜谱举报计数
        recipe.report_count = (recipe.report_count or 0) + 1

        # 检查是否达到自动下架阈值
        if recipe.report_count >= AUTO_OFFLINE_THRESHOLD:
            # 自动下架：设置为待审核状态，取消公开
            recipe.audit_status = "pending"
            recipe.is_public = False

        await db.commit()

        # 返回举报结果
        message = f"举报成功，当前举报次数：{recipe.report_count}"
        if recipe.report_count >= AUTO_OFFLINE_THRESHOLD:
            message += " - 该菜谱已被自动下架，等待审核"

        return APIResponse(
            message=message,
            data={
                "report_id": report_id,
                "report_count": recipe.report_count,
                "auto_offline": recipe.report_count >= AUTO_OFFLINE_THRESHOLD,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"举报失败：{str(e)}")


@router.get("/report/{recipe_id}/count", response_model=dict)
async def get_report_count(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取菜谱举报次数.

    仅管理员或菜谱所有者可查询。
    """
    try:
        result = await db.execute(
            select(Recipe).where(Recipe.id == recipe_id)
        )
        recipe = result.scalar_one_or_none()

        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")

        # 权限检查：仅所有者或管理员可查询（MVP 阶段简化为仅所有者）
        if str(recipe.user_id) != str(current_user.id):
            # TODO: 添加管理员角色检查
            raise HTTPException(status_code=403, detail="无权查询举报信息")

        return {
            "recipe_id": recipe_id,
            "report_count": recipe.report_count,
            "threshold": AUTO_OFFLINE_THRESHOLD,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")
