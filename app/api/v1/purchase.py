"""B 端采购规划 API."""

import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import List, Dict, Optional

from fastapi import APIRouter, HTTPException, Depends, Body, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.purchase_service import PurchaseService
from app.api.schemas import APIResponse

router = APIRouter()


# ============ Schema 定义 ============

class CreateSupplierRequest(BaseModel):
    """创建供应商请求."""
    name: str = Field(..., description="供应商名称", example="XX 农贸批发市场")
    contact_person: Optional[str] = Field(None, description="联系人", example="张三")
    contact_phone: Optional[str] = Field(None, description="联系电话", example="13800138000")
    contact_email: Optional[str] = Field(None, description="联系邮箱", example="zhangsan@example.com")
    address: Optional[str] = Field(None, description="地址", example="XX 市 XX 区 XX 路 100 号")
    categories: Optional[List[str]] = Field(default=None, description="供应品类列表", example=["蔬菜", "水果", "肉类"])
    price_list: Optional[Dict] = Field(default=None, description="价格表", example={"白菜": 2.5, "萝卜": 1.8})


class SupplierItem(BaseModel):
    """供应商项."""
    id: str
    enterprise_id: str
    name: str
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    categories: List[str] = []
    is_active: bool
    rating: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PurchaseOrderItemRequest(BaseModel):
    """采购登单项."""
    ingredient: str = Field(..., description="食材名称")
    quantity: float = Field(..., description="数量", ge=0)
    unit: str = Field(..., description="单位")
    price: float = Field(..., description="单价", ge=0)


class CreatePurchaseOrderRequest(BaseModel):
    """创建采购订单请求."""
    supplier_id: str = Field(..., description="供应商 ID")
    items: List[PurchaseOrderItemRequest] = Field(..., description="订单物品列表")
    expected_date: Optional[str] = Field(None, description="预计到货日期 (YYYY-MM-DD)")
    notes: Optional[str] = Field(None, description="备注", max_length=1024)


class PurchaseOrderItem(BaseModel):
    """采购订单项."""
    id: str
    order_number: str
    supplier_id: str
    status: str
    order_date: date
    expected_date: Optional[date] = None
    received_date: Optional[date] = None
    items: Dict
    total_amount: float
    created_at: datetime

    class Config:
        from_attributes = True


class PurchasePlanResponse(BaseModel):
    """采购计划响应."""
    items: List[Dict] = []
    total_estimated_cost: float = 0
    supplier_summary: List[Dict] = []


# ============ API 端点 ============

@router.get("/suppliers", response_model=List[SupplierItem])
async def list_suppliers(
    enterprise_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取供应商列表."""
    try:
        service = PurchaseService(db)

        # 检查权限
        has_permission = await service.check_enterprise_permission(
            enterprise_id=enterprise_id,
            user_id=str(current_user.id),
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="无权访问该企业")

        # 获取供应商
        suppliers = await service.get_suppliers(enterprise_id=enterprise_id)

        return suppliers

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取供应商失败：{str(e)}")


@router.post("/suppliers", response_model=APIResponse)
async def create_supplier(
    enterprise_id: str,
    request: CreateSupplierRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建供应商."""
    try:
        service = PurchaseService(db)

        # 检查权限
        has_permission = await service.check_enterprise_permission(
            enterprise_id=enterprise_id,
            user_id=str(current_user.id),
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="无权访问该企业")

        # 创建供应商
        supplier = await service.create_supplier(
            enterprise_id=enterprise_id,
            name=request.name,
            contact_person=request.contact_person,
            contact_phone=request.contact_phone,
            contact_email=request.contact_email,
            address=request.address,
            categories=request.categories,
            price_list=request.price_list,
            created_by=str(current_user.id),
        )

        return APIResponse(
            message="供应商创建成功",
            data={"supplier_id": str(supplier.id)},
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建失败：{str(e)}")


@router.post("/plan", response_model=PurchasePlanResponse)
async def generate_purchase_plan(
    enterprise_id: str,
    days: int = Query(7, description="计划天数", ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    生成采购计划.

    基于库存、销量预测、标准化配方生成采购建议。
    """
    try:
        service = PurchaseService(db)

        # 检查权限
        has_permission = await service.check_enterprise_permission(
            enterprise_id=enterprise_id,
            user_id=str(current_user.id),
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="无权访问该企业")

        # 生成采购计划
        plan = await service.generate_purchase_plan(
            enterprise_id=enterprise_id,
            days=days,
        )

        return PurchasePlanResponse(**plan)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成采购计划失败：{str(e)}")


@router.get("/orders", response_model=List[PurchaseOrderItem])
async def list_purchase_orders(
    enterprise_id: str,
    status: Optional[str] = Query(None, description="状态过滤"),
    supplier_id: Optional[str] = Query(None, description="供应商过滤"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取采购订单列表."""
    try:
        service = PurchaseService(db)

        # 检查权限
        has_permission = await service.check_enterprise_permission(
            enterprise_id=enterprise_id,
            user_id=str(current_user.id),
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="无权访问该企业")

        # 获取订单
        orders = await service.get_purchase_orders(
            enterprise_id=enterprise_id,
            status=status,
            supplier_id=supplier_id,
            limit=limit,
        )

        return orders

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取订单失败：{str(e)}")


@router.post("/orders", response_model=APIResponse)
async def create_purchase_order(
    enterprise_id: str,
    request: CreatePurchaseOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建采购订单."""
    try:
        service = PurchaseService(db)

        # 检查权限
        has_permission = await service.check_enterprise_permission(
            enterprise_id=enterprise_id,
            user_id=str(current_user.id),
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="无权访问该企业")

        # 解析预计到货日期
        expected_date = None
        if request.expected_date:
            expected_date = datetime.strptime(request.expected_date, "%Y-%m-%d").date()

        # 创建订单
        order = await service.create_purchase_order(
            enterprise_id=enterprise_id,
            supplier_id=request.supplier_id,
            items=[item.model_dump() for item in request.items],
            expected_date=expected_date,
            created_by=str(current_user.id),
            notes=request.notes,
        )

        return APIResponse(
            message="采购订单创建成功",
            data={"order_id": str(order.id), "order_number": order.order_number},
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建失败：{str(e)}")


@router.patch("/orders/{order_id}/status", response_model=APIResponse)
async def update_order_status(
    order_id: str,
    status: str = Body(..., description="状态：pending/approved/received/cancelled"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新订单状态."""
    try:
        service = PurchaseService(db)

        # 更新状态
        order = await service.update_order_status(
            order_id=order_id,
            status=status,
        )

        return APIResponse(
            message="订单状态更新成功",
            data={"order_id": str(order.id), "status": order.status},
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新失败：{str(e)}")
