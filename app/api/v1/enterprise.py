"""B 端企业用户管理 API."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.enterprise import Enterprise, EnterpriseUser
from app.api.schemas import APIResponse

router = APIRouter()


class EnterpriseRole(str, Enum):
    """企业角色."""
    ADMIN = "admin"  # 企业管理员
    CHEF = "chef"  # 厨师
    MANAGER = "manager"  # 经理
    PURCHASER = "purchaser"  # 采购员
    MEMBER = "member"  # 普通成员


# ============ Schema 定义 ============

class EnterpriseCreateRequest(BaseModel):
    """创建企业请求."""
    name: str = Field(..., description="企业名称", min_length=2, max_length=200, example="某某餐饮有限公司")
    unified_social_credit_code: Optional[str] = Field(None, description="统一社会信用代码", max_length=50)
    legal_representative: Optional[str] = Field(None, description="法人代表", max_length=100)
    contact_phone: Optional[str] = Field(None, description="联系电话", max_length=20)
    contact_email: Optional[str] = Field(None, description="联系邮箱", max_length=100)
    address: Optional[str] = Field(None, description="地址", max_length=500)


class EnterpriseItem(BaseModel):
    """企业项."""
    id: str
    name: str
    unified_social_credit_code: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    is_verified: bool
    plan_type: str
    created_at: datetime


class EnterpriseUserItem(BaseModel):
    """企业用户项."""
    id: str
    user_id: str
    enterprise_id: str
    enterprise_name: str
    role: str
    is_primary: bool
    joined_at: datetime


class EnterpriseDetailResponse(BaseModel):
    """企业详情响应."""
    id: str
    name: str
    unified_social_credit_code: Optional[str] = None
    legal_representative: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None
    is_verified: bool
    is_active: bool
    plan_type: str
    plan_expires_at: Optional[datetime] = None
    member_count: int = 0
    created_at: datetime


# ============ 企业 CRUD API ============

@router.post("/enterprises", response_model=APIResponse)
async def create_enterprise(
    request: EnterpriseCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建企业.

    创建新企业，并自动将当前用户设为管理员 (admin)。
    """
    try:
        # 检查企业名称是否已存在
        result = await db.execute(
            select(Enterprise).where(Enterprise.name == request.name)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="企业名称已存在")

        # 创建企业
        enterprise_id = uuid.uuid4()
        enterprise = Enterprise(
            id=enterprise_id,
            name=request.name,
            unified_social_credit_code=request.unified_social_credit_code,
            legal_representative=request.legal_representative,
            contact_phone=request.contact_phone,
            contact_email=request.contact_email,
            address=request.address,
            is_verified=False,
            is_active=True,
            plan_type="basic",
        )
        db.add(enterprise)
        await db.flush()

        # 创建企业 - 用户关联（管理员）
        enterprise_user = EnterpriseUser(
            id=uuid.uuid4(),
            user_id=current_user.id,
            enterprise_id=enterprise_id,
            role="admin",
            is_primary=True,
            is_active=True,
        )
        db.add(enterprise_user)
        await db.commit()

        return APIResponse(
            message="企业创建成功",
            data={"enterprise_id": str(enterprise_id)},
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建企业失败：{str(e)}")


@router.get("/enterprises/{enterprise_id}", response_model=EnterpriseDetailResponse)
async def get_enterprise(
    enterprise_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取企业详情."""
    try:
        result = await db.execute(
            select(Enterprise).where(Enterprise.id == enterprise_id)
        )
        enterprise = result.scalar_one_or_none()

        if not enterprise:
            raise HTTPException(status_code=404, detail="企业不存在")

        # 检查权限
        user_enterprise = await db.execute(
            select(EnterpriseUser).where(
                EnterpriseUser.user_id == current_user.id,
                EnterpriseUser.enterprise_id == enterprise_id,
                EnterpriseUser.is_active,
            )
        )
        if not user_enterprise.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权访问该企业")

        # 获取成员数量
        count_result = await db.execute(
            select(sa_func.count(EnterpriseUser.id)).where(
                EnterpriseUser.enterprise_id == enterprise_id,
                EnterpriseUser.is_active,
            )
        )
        member_count = count_result.scalar() or 0

        return EnterpriseDetailResponse(
            id=str(enterprise.id),
            name=enterprise.name,
            unified_social_credit_code=enterprise.unified_social_credit_code,
            legal_representative=enterprise.legal_representative,
            contact_phone=enterprise.contact_phone,
            contact_email=enterprise.contact_email,
            address=enterprise.address,
            is_verified=enterprise.is_verified,
            is_active=enterprise.is_active,
            plan_type=enterprise.plan_type,
            plan_expires_at=enterprise.plan_expires_at,
            member_count=member_count,
            created_at=enterprise.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取企业详情失败：{str(e)}")


@router.get("/enterprises", response_model=List[EnterpriseItem])
async def list_user_enterprises(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的所有企业."""
    try:
        result = await db.execute(
            select(Enterprise, EnterpriseUser)
            .join(EnterpriseUser, Enterprise.id == EnterpriseUser.enterprise_id)
            .where(
                EnterpriseUser.user_id == current_user.id,
                EnterpriseUser.is_active,
            )
            .order_by(EnterpriseUser.joined_at.desc())
        )
        rows = result.all()

        return [
            EnterpriseItem(
                id=str(ent.id),
                name=ent.name,
                unified_social_credit_code=ent.unified_social_credit_code,
                contact_phone=ent.contact_phone,
                contact_email=ent.contact_email,
                is_verified=ent.is_verified,
                plan_type=ent.plan_type,
                created_at=ent.created_at,
            )
            for ent, _ in rows
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取企业列表失败：{str(e)}")


# ============ 企业成员管理 ============

@router.get("/enterprises/{enterprise_id}/members", response_model=List[EnterpriseUserItem])
async def list_enterprise_members(
    enterprise_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取企业成员列表."""
    try:
        # 检查权限
        user_enterprise = await db.execute(
            select(EnterpriseUser).where(
                EnterpriseUser.user_id == current_user.id,
                EnterpriseUser.enterprise_id == enterprise_id,
                EnterpriseUser.is_active,
            )
        )
        if not user_enterprise.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权访问该企业")

        result = await db.execute(
            select(EnterpriseUser, User)
            .join(User, EnterpriseUser.user_id == User.id)
            .where(
                EnterpriseUser.enterprise_id == enterprise_id,
                EnterpriseUser.is_active,
            )
            .order_by(EnterpriseUser.joined_at.desc())
        )
        rows = result.all()

        return [
            EnterpriseUserItem(
                id=str(eu.id),
                user_id=str(eu.user_id),
                enterprise_id=str(eu.enterprise_id),
                enterprise_name=ent.name if (ent := next((r[1] for r in []), None)) else "",
                role=eu.role,
                is_primary=eu.is_primary,
                joined_at=eu.joined_at,
            )
            for eu, user in rows
        ]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取成员列表失败：{str(e)}")


@router.post("/enterprises/{enterprise_id}/invite", response_model=APIResponse)
async def invite_member(
    enterprise_id: str,
    phone: str = Body(..., description="被邀请人手机号"),
    role: str = Body("member", description="角色：admin/chef/manager/purchaser/member"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    邀请成员加入企业.

    仅管理员 (admin) 可邀请。
    """
    try:
        # 检查权限
        user_enterprise = await db.execute(
            select(EnterpriseUser).where(
                EnterpriseUser.user_id == current_user.id,
                EnterpriseUser.enterprise_id == enterprise_id,
                EnterpriseUser.role == "admin",
                EnterpriseUser.is_active,
            )
        )
        if not user_enterprise.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="仅管理员可邀请成员")

        # 查找被邀请人
        result = await db.execute(
            select(User).where(User.phone == phone)
        )
        invited_user = result.scalar_one_or_none()

        if not invited_user:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 检查是否已在企业中
        existing = await db.execute(
            select(EnterpriseUser).where(
                EnterpriseUser.user_id == invited_user.id,
                EnterpriseUser.enterprise_id == enterprise_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该用户已在企业中")

        # 创建邀请记录（MVP 阶段直接添加）
        # TODO: 实现邀请码/邀请链接机制
        enterprise_user = EnterpriseUser(
            id=uuid.uuid4(),
            user_id=invited_user.id,
            enterprise_id=enterprise_id,
            role=role,
            is_primary=False,
            is_active=True,
        )
        db.add(enterprise_user)
        await db.commit()

        return APIResponse(message="邀请成功")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"邀请失败：{str(e)}")


@router.put("/enterprises/{enterprise_id}/members/{user_id}/role", response_model=APIResponse)
async def update_member_role(
    enterprise_id: str,
    user_id: str,
    role: str = Body(..., description="角色：admin/chef/manager/purchaser/member"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新成员角色.

    仅管理员 (admin) 可操作。
    """
    try:
        # 检查权限
        user_enterprise = await db.execute(
            select(EnterpriseUser).where(
                EnterpriseUser.user_id == current_user.id,
                EnterpriseUser.enterprise_id == enterprise_id,
                EnterpriseUser.role == "admin",
                EnterpriseUser.is_active,
            )
        )
        if not user_enterprise.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="仅管理员可操作")

        # 更新角色
        result = await db.execute(
            select(EnterpriseUser).where(
                EnterpriseUser.user_id == user_id,
                EnterpriseUser.enterprise_id == enterprise_id,
            )
        )
        enterprise_user = result.scalar_one_or_none()

        if not enterprise_user:
            raise HTTPException(status_code=404, detail="成员不存在")

        enterprise_user.role = role
        await db.commit()

        return APIResponse(message="角色更新成功")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新失败：{str(e)}")


@router.delete("/enterprises/{enterprise_id}/members/{user_id}", response_model=APIResponse)
async def remove_member(
    enterprise_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    移除成员.

    仅管理员 (admin) 可操作，或用户自行退出。
    """
    try:
        # 检查权限
        user_enterprise = await db.execute(
            select(EnterpriseUser).where(
                EnterpriseUser.user_id == current_user.id,
                EnterpriseUser.enterprise_id == enterprise_id,
                EnterpriseUser.is_active,
            )
        )
        current_eu = user_enterprise.scalar_one_or_none()
        if not current_eu:
            raise HTTPException(status_code=403, detail="无权操作")

        # 查找目标成员
        result = await db.execute(
            select(EnterpriseUser).where(
                EnterpriseUser.user_id == user_id,
                EnterpriseUser.enterprise_id == enterprise_id,
            )
        )
        target_eu = result.scalar_one_or_none()

        if not target_eu:
            raise HTTPException(status_code=404, detail="成员不存在")

        # 权限检查：管理员可移除任何人，或用户自行退出
        if current_eu.role != "admin" and current_eu.user_id != target_eu.user_id:
            raise HTTPException(status_code=403, detail="无权移除该成员")

        # 不能移除唯一管理员
        if target_eu.role == "admin":
            admin_count = await db.execute(
                select(sa_func.count(EnterpriseUser.id)).where(
                    EnterpriseUser.enterprise_id == enterprise_id,
                    EnterpriseUser.role == "admin",
                    EnterpriseUser.is_active,
                )
            )
            if admin_count.scalar() == 1:
                raise HTTPException(status_code=400, detail="不能移除唯一的管理员")

        # 软删除
        target_eu.is_active = False
        await db.commit()

        return APIResponse(message="操作成功")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"操作失败：{str(e)}")
