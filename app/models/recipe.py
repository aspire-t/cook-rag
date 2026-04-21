"""Recipe 模型 - 菜谱主表."""

from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Computed,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from . import Base


class Recipe(Base):
    """菜谱主表."""

    __tablename__ = "recipes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)

    # 关联用户/企业（可选，系统菜谱为 NULL）
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    enterprise_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )  # MVP 阶段暂不实现

    # 菜系分类
    cuisine: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # 难度和时间
    difficulty: Mapped[str | None] = mapped_column(
        String(20),
        CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name="check_difficulty"),
        nullable=True,
        index=True,
    )
    prep_time: Mapped[int | None] = mapped_column(
        Integer,
        CheckConstraint("prep_time >= 0", name="check_prep_time"),
        nullable=True,
    )  # 准备时间（分钟）
    cook_time: Mapped[int | None] = mapped_column(
        Integer,
        CheckConstraint("cook_time >= 0", name="check_cook_time"),
        nullable=True,
    )  # 烹饪时间（分钟）
    servings: Mapped[int | None] = mapped_column(
        Integer,
        CheckConstraint("servings > 0", name="check_servings"),
        default=1,
        nullable=True,
    )  # 几人份

    # 标签 (JSONB 数组)
    # 示例：["辣", "快手菜", "一锅出", "下饭"]
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # 来源
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(20),
        default="system",
        nullable=False,
    )  # system/howtocook/ugc

    # 公开状态
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 审核状态（UGC 菜谱用）
    audit_status: Mapped[str] = mapped_column(
        String(20),
        default="approved",
        nullable=False,
    )  # pending/approved/rejected
    rejected_reason: Mapped[str | None] = mapped_column(nullable=True)

    # 举报计数
    report_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 统计
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    favorite_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Qdrant 向量 ID（用于检索关联）
    vector_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

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
    user: Mapped["User"] = relationship(back_populates="recipes")
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
    )
    steps: Mapped[list["RecipeStep"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
    )
    reports: Mapped[list["Report"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_recipes_public_audit", "is_public", "audit_status", postgresql_where="is_public = true"),
    )

    def __repr__(self) -> str:
        return f"<Recipe(id={self.id}, name={self.name}, cuisine={self.cuisine})>"
