"""B 端库存管理模型."""

import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from . import Base


class Inventory(Base):
    """库存表 (B 端)."""

    __tablename__ = "inventory"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # 关联企业
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enterprises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="企业 ID",
    )

    # 食材信息
    ingredient_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="食材名称")
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0, comment="当前库存数量")
    unit: Mapped[str] = mapped_column(String(20), nullable=False, comment="单位 (kg/g/L/个等)")

    # 库存预警
    min_stock: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True, comment="最低库存警戒线")
    max_stock: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True, comment="最高库存警戒线")

    # 保质期管理
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True, comment="保质期日期")
    batch_number: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="批次号")

    # 库位管理
    location: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="库位")

    # 审计字段
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
    enterprise: Mapped["Enterprise"] = relationship(back_populates="inventory")
    transactions: Mapped[list["InventoryTransaction"]] = relationship(
        back_populates="inventory",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Inventory(enterprise_id={self.enterprise_id}, ingredient={self.ingredient_name}, quantity={self.quantity})>"


class InventoryTransaction(Base):
    """库存交易记录表."""

    __tablename__ = "inventory_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # 关联企业
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enterprises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="企业 ID",
    )

    # 关联库存
    inventory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="库存 ID",
    )

    # 食材信息
    ingredient_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="食材名称")

    # 变动信息
    change_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="变动数量（正数入库，负数出库）")
    transaction_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="交易类型：stock_in(入库)/stock_out(出库)/adjustment(调整)/expiry(过期)",
    )

    # 变动前后快照
    before_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="变动前数量")
    after_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="变动后数量")

    # 备注
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # 操作人
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="操作人 ID",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # 关联
    enterprise: Mapped["Enterprise"] = relationship(back_populates="inventory_transactions")
    inventory: Mapped["Inventory"] = relationship(back_populates="transactions")
    user: Mapped["User"] = relationship(back_populates="inventory_transactions")

    def __repr__(self) -> str:
        return f"<InventoryTransaction(ingredient={self.ingredient_name}, change={self.change_quantity}, type={self.transaction_type})>"
