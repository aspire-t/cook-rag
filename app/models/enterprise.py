"""Enterprise 模型 - B 端企业用户."""

from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from . import Base


class Enterprise(Base):
    """企业表."""

    __tablename__ = "enterprises"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="企业名称")
    unified_social_credit_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="统一社会信用代码"
    )
    legal_representative: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="法人代表")

    # 联系信息
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 企业认证状态
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已认证")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 企业状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否激活")

    # 套餐信息
    plan_type: Mapped[str] = mapped_column(
        String(20),
        default="basic",
        comment="套餐类型：basic/standard/premium",
    )
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
    users: Mapped[list["EnterpriseUser"]] = relationship(
        back_populates="enterprise",
        cascade="all, delete-orphan",
    )

    # 企业菜谱（后续迭代）
    # enterprise_recipes: Mapped[list["Recipe"]] = relationship(back_populates="enterprise")

    def __repr__(self) -> str:
        return f"<Enterprise(id={self.id}, name={self.name})>"


class EnterpriseUser(Base):
    """企业 - 用户关联表（支持多企业）."""

    __tablename__ = "enterprise_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # 关联用户
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 关联企业
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enterprises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 企业内角色
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="member",
        comment="角色：admin/chef/manager/purchaser/member",
    )

    # 是否为主企业
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为主企业")

    # 加入时间
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否激活")

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
    user: Mapped["User"] = relationship(back_populates="enterprise_users")
    enterprise: Mapped["Enterprise"] = relationship(back_populates="users")

    __table_args__ = (
        Index("idx_enterprise_users_user_enterprise", "user_id", "enterprise_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<EnterpriseUser(user_id={self.user_id}, enterprise_id={self.enterprise_id}, role={self.role})>"
