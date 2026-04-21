"""供应商模型 - 独立文件（避免循环导入）."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from . import Base


class Supplier(Base):
    """供应商表 (B 端)."""

    __tablename__ = "suppliers"

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

    # 供应商信息
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="供应商名称")
    contact_person: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="联系人")
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="联系电话")
    contact_email: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="联系邮箱")
    address: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="地址")

    # 供应信息
    categories: Mapped[list] = mapped_column(JSONB, default=list, nullable=False, comment="供应品类列表")
    price_list: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False, comment="价格表 (JSON)")

    # 状态和评级
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否激活")
    rating: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True, comment="评级 (1.0-5.0)")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

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

    def __repr__(self) -> str:
        return f"<Supplier(id={self.id}, name={self.name})>"
