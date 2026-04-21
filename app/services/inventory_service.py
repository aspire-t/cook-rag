"""B 端库存管理服务."""

import uuid
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func
from sqlalchemy.orm import joinedload

from app.models.inventory import Inventory, InventoryTransaction
from app.models.enterprise import EnterpriseUser


class TransactionType(str, Enum):
    """交易类型."""
    STOCK_IN = "stock_in"  # 入库
    STOCK_OUT = "stock_out"  # 出库
    ADJUSTMENT = "adjustment"  # 调整
    EXPIRY = "expiry"  # 过期


class InventoryService:
    """库存管理服务."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_enterprise_permission(
        self,
        enterprise_id: str,
        user_id: str,
    ) -> bool:
        """检查用户是否属于该企业."""
        result = await self.db.execute(
            select(EnterpriseUser).where(
                EnterpriseUser.enterprise_id == enterprise_id,
                EnterpriseUser.user_id == user_id,
                EnterpriseUser.is_active,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_inventory(
        self,
        enterprise_id: str,
        ingredient_name: Optional[str] = None,
    ) -> List[Inventory]:
        """获取库存列表."""
        query = select(Inventory).where(
            Inventory.enterprise_id == enterprise_id,
        )
        if ingredient_name:
            query = query.where(Inventory.ingredient_name == ingredient_name)
        query = query.order_by(Inventory.ingredient_name)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def stock_in(
        self,
        enterprise_id: str,
        ingredient_name: str,
        quantity: Decimal,
        unit: str,
        expiry_date: Optional[date] = None,
        batch_number: Optional[str] = None,
        location: Optional[str] = None,
        created_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Inventory:
        """
        入库操作.

        Args:
            enterprise_id: 企业 ID
            ingredient_name: 食材名称
            quantity: 入库数量
            unit: 单位
            expiry_date: 保质期日期
            batch_number: 批次号
            location: 库位
            created_by: 操作人 ID
            notes: 备注

        Returns:
            Inventory: 库存记录
        """
        # 查找现有库存
        result = await self.db.execute(
            select(Inventory).where(
                Inventory.enterprise_id == enterprise_id,
                Inventory.ingredient_name == ingredient_name,
            )
        )
        inventory = result.scalar_one_or_none()

        if inventory:
            # 更新现有库存
            before_quantity = inventory.quantity
            inventory.quantity += quantity
            inventory.unit = unit
            if expiry_date:
                inventory.expiry_date = expiry_date
            if batch_number:
                inventory.batch_number = batch_number
            if location:
                inventory.location = location
            after_quantity = inventory.quantity
        else:
            # 创建新库存
            inventory = Inventory(
                id=uuid.uuid4(),
                enterprise_id=enterprise_id,
                ingredient_name=ingredient_name,
                quantity=quantity,
                unit=unit,
                expiry_date=expiry_date,
                batch_number=batch_number,
                location=location,
            )
            before_quantity = Decimal(0)
            after_quantity = quantity
            self.db.add(inventory)

        await self.db.flush()

        # 记录交易
        await self._create_transaction(
            enterprise_id=enterprise_id,
            inventory_id=inventory.id,
            ingredient_name=ingredient_name,
            change_quantity=quantity,
            transaction_type=TransactionType.STOCK_IN,
            before_quantity=before_quantity,
            after_quantity=after_quantity,
            created_by=created_by,
            notes=notes,
        )

        return inventory

    async def stock_out(
        self,
        enterprise_id: str,
        ingredient_name: str,
        quantity: Decimal,
        created_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Inventory:
        """
        出库操作.

        Args:
            enterprise_id: 企业 ID
            ingredient_name: 食材名称
            quantity: 出库数量
            created_by: 操作人 ID
            notes: 备注

        Returns:
            Inventory: 库存记录
        """
        result = await self.db.execute(
            select(Inventory).where(
                Inventory.enterprise_id == enterprise_id,
                Inventory.ingredient_name == ingredient_name,
            )
        )
        inventory = result.scalar_one_or_none()

        if not inventory:
            raise ValueError(f"食材 {ingredient_name} 不存在于库存中")

        if inventory.quantity < quantity:
            raise ValueError(f"库存不足：当前 {inventory.quantity} {inventory.unit}, 需要 {quantity} {inventory.unit}")

        before_quantity = inventory.quantity
        inventory.quantity -= quantity
        after_quantity = inventory.quantity

        await self.db.flush()

        # 记录交易
        await self._create_transaction(
            enterprise_id=enterprise_id,
            inventory_id=inventory.id,
            ingredient_name=ingredient_name,
            change_quantity=-quantity,
            transaction_type=TransactionType.STOCK_OUT,
            before_quantity=before_quantity,
            after_quantity=after_quantity,
            created_by=created_by,
            notes=notes,
        )

        return inventory

    async def _create_transaction(
        self,
        enterprise_id: str,
        inventory_id: uuid.UUID,
        ingredient_name: str,
        change_quantity: Decimal,
        transaction_type: TransactionType,
        before_quantity: Decimal,
        after_quantity: Decimal,
        created_by: Optional[str] = None,
        notes: Optional[str] = None,
    ):
        """创建交易记录."""
        transaction = InventoryTransaction(
            id=uuid.uuid4(),
            enterprise_id=enterprise_id,
            inventory_id=inventory_id,
            ingredient_name=ingredient_name,
            change_quantity=change_quantity,
            transaction_type=transaction_type.value,
            before_quantity=before_quantity,
            after_quantity=after_quantity,
            created_by=created_by,
            notes=notes,
        )
        self.db.add(transaction)

    async def check_stock_alerts(
        self,
        enterprise_id: str,
    ) -> Tuple[List[Inventory], List[Inventory]]:
        """
        检查库存预警.

        Returns:
            Tuple[List[Inventory], List[Inventory]]: (库存不足列表，库存过剩列表)
        """
        # 库存不足
        low_stock_result = await self.db.execute(
            select(Inventory).where(
                Inventory.enterprise_id == enterprise_id,
                Inventory.min_stock.isnot(None),
                Inventory.quantity <= Inventory.min_stock,
            )
        )
        low_stock = low_stock_result.scalars().all()

        # 库存过剩
        over_stock_result = await self.db.execute(
            select(Inventory).where(
                Inventory.enterprise_id == enterprise_id,
                Inventory.max_stock.isnot(None),
                Inventory.quantity >= Inventory.max_stock,
            )
        )
        over_stock = over_stock_result.scalars().all()

        return low_stock, over_stock

    async def check_expiring_items(
        self,
        enterprise_id: str,
        days: int = 7,
    ) -> List[Inventory]:
        """
        检查即将过期的食材.

        Args:
            enterprise_id: 企业 ID
            days: 预警天数

        Returns:
            List[Inventory]: 即将过期的食材列表
        """
        expiry_threshold = date.today() + timedelta(days=days)
        result = await self.db.execute(
            select(Inventory).where(
                Inventory.enterprise_id == enterprise_id,
                Inventory.expiry_date.isnot(None),
                Inventory.expiry_date <= expiry_threshold,
                Inventory.expiry_date >= date.today(),
            )
        )
        return result.scalars().all()

    async def check_expired_items(
        self,
        enterprise_id: str,
    ) -> List[Inventory]:
        """
        检查已过期的食材.

        Args:
            enterprise_id: 企业 ID

        Returns:
            List[Inventory]: 已过期的食材列表
        """
        result = await self.db.execute(
            select(Inventory).where(
                Inventory.enterprise_id == enterprise_id,
                Inventory.expiry_date.isnot(None),
                Inventory.expiry_date < date.today(),
            )
        )
        return result.scalars().all()

    async def get_transaction_history(
        self,
        enterprise_id: str,
        ingredient_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[InventoryTransaction]:
        """获取交易历史记录."""
        query = select(InventoryTransaction).where(
            InventoryTransaction.enterprise_id == enterprise_id,
        )
        if ingredient_name:
            query = query.where(InventoryTransaction.ingredient_name == ingredient_name)
        query = query.order_by(InventoryTransaction.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
