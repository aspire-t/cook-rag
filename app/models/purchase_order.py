"""B 端采购订单模型."""

import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from . import Base
from .supplier import Supplier


class PurchaseOrder(Base):
    """采购订单表 (B 端)."""

    __tablename__ = "purchase_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # 关联企业和供应商
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enterprises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="企业 ID",
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="供应商 ID",
    )

    # 订单信息
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="订单号")
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        comment="状态：pending/approved/received/cancelled",
        index=True,
    )
    order_date: Mapped[date] = mapped_column(Date, nullable=False, comment="下单日期")
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="预计到货日期")
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="实际到货日期")

    # 订单物品 (JSON)
    # 示例：[{"ingredient": "鸡肉", "quantity": 10, "unit": "kg", "price": 18, "amount": 180}]
    items: Mapped[dict] = mapped_column(JSONB, nullable=False, comment="订单物品列表")

    # 金额
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0, comment="总金额")

    # 备注
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # 操作人
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="创建人 ID",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # 关联
    enterprise: Mapped["Enterprise"] = relationship(back_populates="purchase_orders")
    supplier: Mapped["Supplier"] = relationship(back_populates="purchase_orders")
    user: Mapped["User"] = relationship(back_populates="purchase_orders")

    def __repr__(self) -> str:
        return f"<PurchaseOrder(order_number={self.order_number}, status={self.status}, total={self.total_amount})>"
