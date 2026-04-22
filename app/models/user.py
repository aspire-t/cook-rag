"""User 模型 - C 端用户."""

from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from . import Base


class User(Base):
    """用户表 (C 端)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    nickname: Mapped[str | None] = mapped_column(String(50), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 口味偏好 (JSONB)
    # 示例：{"spicy": 0.8, "sweet": 0.3, "sour": 0.5, "salty": 0.6}
    taste_prefs: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # 饮食限制 (JSONB 数组)
    # 示例：["素食", "无麸质", "无牛肉"]
    dietary_restrictions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # 微信相关（小程序登录用）
    wechat_openid: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    wechat_unionid: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    recipes: Mapped[list["Recipe"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    enterprise_users: Mapped[list["EnterpriseUser"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    search_histories: Mapped[list["SearchHistory"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    reports: Mapped[list["Report"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    inventory_transactions: Mapped[list["InventoryTransaction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, phone={self.phone}, nickname={self.nickname})>"
