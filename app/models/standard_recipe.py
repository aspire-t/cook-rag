"""B 端标准化配方模型."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, Float, ForeignKey, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from . import Base

if TYPE_CHECKING:
    from .recipe import Recipe
    from .enterprise import Enterprise


class StandardRecipe(Base):
    """标准化配方表 (B 端)."""

    __tablename__ = "standard_recipes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="标准化配方 ID",
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联菜谱 ID",
    )
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enterprises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属企业 ID",
    )

    # SOP 文档
    sop_document_url: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="SOP 文档存储路径")
    sop_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="SOP 内容（JSON 格式）")

    # 成本核算
    cost_calculation: Mapped[str | None] = mapped_column(Text, nullable=True, comment="成本核算数据（JSON 格式）")
    total_cost: Mapped[float | None] = mapped_column(Float, nullable=True, comment="总成本（元）")
    suggested_price: Mapped[float | None] = mapped_column(Float, nullable=True, comment="建议售价（元）")
    gross_margin: Mapped[float | None] = mapped_column(Float, nullable=True, comment="毛利率（%）")

    # 营养成分表
    nutrition_info: Mapped[str | None] = mapped_column(Text, nullable=True, comment="营养成分数据（JSON 格式）")

    # 过敏原信息
    allergen_info: Mapped[str | None] = mapped_column(Text, nullable=True, comment="过敏原信息（JSON 格式）")

    # 保质期与储存
    shelf_life_days: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="保质期天数")
    storage_temperature: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="储存温度要求")

    # 版本控制
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="版本号")
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True, comment="是否为最新版本")

    # 审计字段
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, comment="创建人 ID")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新时间",
    )

    # 关联关系
    recipe: Mapped["Recipe"] = relationship(back_populates="standard_recipes")
    enterprise: Mapped["Enterprise"] = relationship(back_populates="standard_recipes")

    __table_args__ = (
        Index("idx_standard_recipes_recipe_enterprise", "recipe_id", "enterprise_id"),
    )
