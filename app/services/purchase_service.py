"""B 端采购规划服务."""

import uuid
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func
from sqlalchemy.orm import joinedload

from app.models.purchase_order import Supplier, PurchaseOrder
from app.models.inventory import Inventory
from app.models.standard_recipe import StandardRecipe
from app.models.enterprise import EnterpriseUser
from app.services.llm_service import LLMService


# 采购规划生成 Prompt
B_PURCHASE_PLAN_PROMPT = """
# Role
你是一位资深采购经理，擅长根据餐厅经营数据制定最优采购计划。

# Context
## 当前库存
{current_inventory}

## 未来 7 天预测销量
{sales_forecast}

## 菜谱配方
{recipe_formulas}

## 供应商信息
{suppliers}

# Task
生成未来 7 天的采购计划，目标：
1. 确保食材充足，不断货
2. 最小化库存积压，减少损耗
3. 利用供应商优惠，降低成本

# Output Format

## 采购清单
| 食材 | 需求量 | 当前库存 | 需采购 | 优先供应商 | 单价 | 总价 | 建议下单日期 |
|------|--------|----------|--------|------------|------|------|-------------|
| 鸡胸肉 | 50kg | 15kg | 35kg | XX 农贸 | 18 元/kg | 630 元 | 周一/周四 |

## 成本分析
- 预计采购总额：XXXX 元
- 对比上周：+X% / -X%
- 成本优化建议：...
"""


class PurchaseService:
    """采购规划管理服务."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()

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

    async def generate_purchase_plan(
        self,
        enterprise_id: str,
        days: int = 7,
    ) -> Dict:
        """
        生成采购计划.

        基于库存、销量预测、标准化配方生成采购建议。
        """
        # 获取当前库存
        inventory_result = await self.db.execute(
            select(Inventory).where(Inventory.enterprise_id == enterprise_id)
        )
        inventory_list = inventory_result.scalars().all()

        # 获取供应商
        suppliers_result = await self.db.execute(
            select(Supplier).where(
                Supplier.enterprise_id == enterprise_id,
                Supplier.is_active,
            )
        )
        suppliers = suppliers_result.scalars().all()

        # 构建 Prompt 输入
        inventory_text = "\n".join(
            f"- {inv.ingredient_name}: {inv.quantity} {inv.unit}"
            for inv in inventory_list
        ) or "暂无库存数据"

        suppliers_text = "\n".join(
            f"- {s.name}: {s.categories}, 联系方式：{s.contact_phone}"
            for s in suppliers
        ) or "暂无供应商数据"

        # 简单的需求预测（MVP 版本，后续可接入销量数据）
        # 这里假设每天需要库存量的 2 倍作为安全库存
        purchase_items = []
        for inv in inventory_list:
            if inv.min_stock is not None and inv.quantity < inv.min_stock:
                needed = inv.min_stock - inv.quantity
                # 查找最优供应商
                supplier = self._find_best_supplier(suppliers, inv.ingredient_name)
                if supplier:
                    purchase_items.append({
                        "ingredient": inv.ingredient_name,
                        "needed": float(needed),
                        "unit": inv.unit,
                        "supplier": supplier.name,
                        "estimated_price": self._get_price(supplier, inv.ingredient_name),
                    })

        # 调用 LLM 优化采购计划
        prompt = B_PURCHASE_PLAN_PROMPT.format(
            current_inventory=inventory_text,
            sales_forecast="待接入销量预测数据",
            recipe_formulas="待接入配方数据",
            suppliers=suppliers_text,
        )

        # LLM 生成建议（MVP 版本简化处理）
        plan = {
            "items": purchase_items,
            "total_estimated_cost": sum(item["needed"] * item["estimated_price"] for item in purchase_items),
            "supplier_summary": self._group_by_supplier(purchase_items),
        }

        return plan

    def _find_best_supplier(self, suppliers: List[Supplier], ingredient: str) -> Optional[Supplier]:
        """查找最佳供应商."""
        for supplier in suppliers:
            if ingredient in supplier.categories:
                return supplier
        return suppliers[0] if suppliers else None

    def _get_price(self, supplier: Supplier, ingredient: str) -> float:
        """获取供应商价格."""
        return supplier.price_list.get(ingredient, 0)

    def _group_by_supplier(self, items: List[Dict]) -> List[Dict]:
        """按供应商汇总."""
        summary = {}
        for item in items:
            supplier = item["supplier"]
            if supplier not in summary:
                summary[supplier] = {"supplier": supplier, "total": 0, "items": []}
            summary[supplier]["total"] += item["needed"] * item["estimated_price"]
            summary[supplier]["items"].append(item["ingredient"])
        return list(summary.values())

    async def create_purchase_order(
        self,
        enterprise_id: str,
        supplier_id: str,
        items: List[Dict],
        expected_date: Optional[date] = None,
        created_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PurchaseOrder:
        """
        创建采购订单.

        Args:
            enterprise_id: 企业 ID
            supplier_id: 供应商 ID
            items: 订单物品列表 [{"ingredient": "鸡肉", "quantity": 10, "unit": "kg", "price": 18}]
            expected_date: 预计到货日期
            created_by: 创建人 ID
            notes: 备注

        Returns:
            PurchaseOrder: 采购订单对象
        """
        # 生成订单号
        order_number = f"PO{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 计算总金额
        total_amount = sum(
            Decimal(str(item["quantity"])) * Decimal(str(item["price"]))
            for item in items
        )

        # 创建订单
        order = PurchaseOrder(
            id=uuid.uuid4(),
            enterprise_id=enterprise_id,
            supplier_id=supplier_id,
            order_number=order_number,
            status="pending",
            order_date=date.today(),
            expected_date=expected_date,
            items={"items": items},
            total_amount=total_amount,
            created_by=created_by,
            notes=notes,
        )

        self.db.add(order)
        await self.db.flush()

        return order

    async def get_purchase_orders(
        self,
        enterprise_id: str,
        status: Optional[str] = None,
        supplier_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[PurchaseOrder]:
        """获取采购订单列表."""
        query = select(PurchaseOrder).where(
            PurchaseOrder.enterprise_id == enterprise_id,
        )
        if status:
            query = query.where(PurchaseOrder.status == status)
        if supplier_id:
            query = query.where(PurchaseOrder.supplier_id == supplier_id)
        query = query.order_by(PurchaseOrder.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_order_status(
        self,
        order_id: str,
        status: str,
        received_date: Optional[date] = None,
    ) -> PurchaseOrder:
        """更新订单状态."""
        result = await self.db.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise ValueError(f"订单不存在：{order_id}")

        order.status = status
        if received_date:
            order.received_date = received_date
        elif status == "received":
            order.received_date = date.today()

        await self.db.flush()
        return order

    async def get_suppliers(
        self,
        enterprise_id: str,
        is_active: bool = True,
    ) -> List[Supplier]:
        """获取供应商列表."""
        query = select(Supplier).where(Supplier.enterprise_id == enterprise_id)
        if is_active:
            query = query.where(Supplier.is_active)
        query = query.order_by(Supplier.name)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_supplier(
        self,
        enterprise_id: str,
        name: str,
        contact_person: Optional[str] = None,
        contact_phone: Optional[str] = None,
        contact_email: Optional[str] = None,
        address: Optional[str] = None,
        categories: Optional[List[str]] = None,
        price_list: Optional[Dict] = None,
        created_by: Optional[str] = None,
    ) -> Supplier:
        """创建供应商."""
        supplier = Supplier(
            id=uuid.uuid4(),
            enterprise_id=enterprise_id,
            name=name,
            contact_person=contact_person,
            contact_phone=contact_phone,
            contact_email=contact_email,
            address=address,
            categories=categories or [],
            price_list=price_list or {},
            created_by=created_by,
        )
        self.db.add(supplier)
        await self.db.flush()
        return supplier
