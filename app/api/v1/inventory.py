"""B 端库存管理 API."""

import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Body, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.inventory_service import InventoryService, TransactionType
from app.api.schemas import APIResponse

router = APIRouter()


# ============ Schema 定义 ============

class StockInRequest(BaseModel):
    """入库请求."""
    ingredient_name: str = Field(..., description="食材名称", example="鸡胸肉")
    quantity: float = Field(..., description="入库数量", ge=0, example=10.5)
    unit: str = Field(..., description="单位", example="kg")
    expiry_date: Optional[str] = Field(None, description="保质期日期 (YYYY-MM-DD)", example="2026-05-01")
    batch_number: Optional[str] = Field(None, description="批次号", example="BATCH20260421")
    location: Optional[str] = Field(None, description="库位", example="A-01-02")
    notes: Optional[str] = Field(None, description="备注", max_length=1024)


class StockOutRequest(BaseModel):
    """出库请求."""
    ingredient_name: str = Field(..., description="食材名称", example="鸡胸肉")
    quantity: float = Field(..., description="出库数量", ge=0, example=5.0)
    notes: Optional[str] = Field(None, description="备注", max_length=1024)


class InventoryItem(BaseModel):
    """库存项."""
    id: str
    enterprise_id: str
    ingredient_name: str
    quantity: float
    unit: str
    min_stock: Optional[float] = None
    max_stock: Optional[float] = None
    expiry_date: Optional[str] = None
    batch_number: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionItem(BaseModel):
    """交易记录项."""
    id: str
    enterprise_id: str
    ingredient_name: str
    change_quantity: float
    transaction_type: str
    before_quantity: float
    after_quantity: float
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StockAlertResponse(BaseModel):
    """库存预警响应."""
    low_stock: List[InventoryItem] = []
    over_stock: List[InventoryItem] = []
    expiring_soon: List[InventoryItem] = []
    expired: List[InventoryItem] = []


# ============ API 端点 ============

@router.get("", response_model=List[InventoryItem])
async def list_inventory(
    enterprise_id: str,
    ingredient_name: Optional[str] = Query(None, description="食材名称过滤"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取库存列表."""
    try:
        service = InventoryService(db)

        # 检查权限
        has_permission = await service.check_enterprise_permission(
            enterprise_id=enterprise_id,
            user_id=str(current_user.id),
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="无权访问该企业")

        # 获取库存
        inventories = await service.get_inventory(
            enterprise_id=enterprise_id,
            ingredient_name=ingredient_name,
        )

        return inventories

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取库存失败：{str(e)}")


@router.post("/stock-in", response_model=APIResponse)
async def stock_in(
    enterprise_id: str,
    request: StockInRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    入库操作.

    新增或更新库存记录，自动记录交易流水。
    """
    try:
        service = InventoryService(db)

        # 检查权限
        has_permission = await service.check_enterprise_permission(
            enterprise_id=enterprise_id,
            user_id=str(current_user.id),
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="无权访问该企业")

        # 解析保质期日期
        expiry_date = None
        if request.expiry_date:
            expiry_date = datetime.strptime(request.expiry_date, "%Y-%m-%d").date()

        # 入库
        inventory = await service.stock_in(
            enterprise_id=enterprise_id,
            ingredient_name=request.ingredient_name,
            quantity=Decimal(str(request.quantity)),
            unit=request.unit,
            expiry_date=expiry_date,
            batch_number=request.batch_number,
            location=request.location,
            created_by=str(current_user.id),
            notes=request.notes,
        )

        return APIResponse(
            message="入库成功",
            data={"inventory_id": str(inventory.id), "quantity": str(inventory.quantity)},
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"入库失败：{str(e)}")


@router.post("/stock-out", response_model=APIResponse)
async def stock_out(
    enterprise_id: str,
    request: StockOutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    出库操作.

    减少库存，自动记录交易流水。
    """
    try:
        service = InventoryService(db)

        # 检查权限
        has_permission = await service.check_enterprise_permission(
            enterprise_id=enterprise_id,
            user_id=str(current_user.id),
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="无权访问该企业")

        # 出库
        inventory = await service.stock_out(
            enterprise_id=enterprise_id,
            ingredient_name=request.ingredient_name,
            quantity=Decimal(str(request.quantity)),
            created_by=str(current_user.id),
            notes=request.notes,
        )

        return APIResponse(
            message="出库成功",
            data={"inventory_id": str(inventory.id), "remaining_quantity": str(inventory.quantity)},
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"出库失败：{str(e)}")


@router.get("/alert", response_model=StockAlertResponse)
async def get_stock_alerts(
    enterprise_id: str,
    expiry_days: int = Query(7, description="保质期预警天数", ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取库存预警.

    包括：
    - 库存不足（低于 min_stock）
    - 库存过剩（高于 max_stock）
    - 即将过期（expiry_days 天内）
    - 已过期
    """
    try:
        service = InventoryService(db)

        # 检查权限
        has_permission = await service.check_enterprise_permission(
            enterprise_id=enterprise_id,
            user_id=str(current_user.id),
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="无权访问该企业")

        # 获取预警
        low_stock, over_stock = await service.check_stock_alerts(enterprise_id=enterprise_id)
        expiring_soon = await service.check_expiring_items(enterprise_id=enterprise_id, days=expiry_days)
        expired = await service.check_expired_items(enterprise_id=enterprise_id)

        return StockAlertResponse(
            low_stock=low_stock,
            over_stock=over_stock,
            expiring_soon=expiring_soon,
            expired=expired,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取预警失败：{str(e)}")


@router.get("/transactions", response_model=List[TransactionItem])
async def list_transactions(
    enterprise_id: str,
    ingredient_name: Optional[str] = Query(None, description="食材名称过滤"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取库存交易历史记录."""
    try:
        service = InventoryService(db)

        # 检查权限
        has_permission = await service.check_enterprise_permission(
            enterprise_id=enterprise_id,
            user_id=str(current_user.id),
        )
        if not has_permission:
            raise HTTPException(status_code=403, detail="无权访问该企业")

        # 获取交易记录
        transactions = await service.get_transaction_history(
            enterprise_id=enterprise_id,
            ingredient_name=ingredient_name,
            limit=limit,
        )

        return transactions

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取交易记录失败：{str(e)}")
