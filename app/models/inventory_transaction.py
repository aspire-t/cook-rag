"""库存交易记录模型 - 独立版本（避免循环导入）."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Text, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID


class InventoryTransactionBase(DeclarativeBase):
    """库存交易记录独立 Base."""
    pass


class InventoryTransaction(InventoryTransactionBase):
    """库存交易记录表（独立版本，用于避免循环导入）."""

    __tablename__ = "inventory_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # 关联企业
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="企业 ID",
    )

    # 关联库存
    inventory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="库存 ID",
    )

    # 食材信息
    ingredient_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="食材名称")

    # 变动信息
    change_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="变动数量")
    transaction_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="交易类型：stock_in/stock_out/adjustment/expiry",
    )

    # 变动前后快照
    before_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="变动前数量")
    after_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="变动后数量")

    # 备注
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # 操作人
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="操作人 ID",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<InventoryTransaction(ingredient={self.ingredient_name}, change={self.change_quantity})>"
