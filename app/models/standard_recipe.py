"""B 端标准化配方模型."""

from sqlalchemy import Column, String, Integer, Boolean, Float, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


class StandardRecipe(Base):
    """标准化配方表 (B 端)."""

    __tablename__ = "standard_recipes"

    id = Column(String(36), primary_key=True, comment="标准化配方 ID")
    recipe_id = Column(
        String(36),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联菜谱 ID",
    )
    enterprise_id = Column(
        String(36),
        ForeignKey("enterprises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属企业 ID",
    )

    # SOP 文档
    sop_document_url = Column(String(255), nullable=True, comment="SOP 文档存储路径")
    sop_content = Column(Text, nullable=True, comment="SOP 内容（JSON 格式）")

    # 成本核算
    cost_calculation = Column(Text, nullable=True, comment="成本核算数据（JSON 格式）")
    total_cost = Column(Float, nullable=True, comment="总成本（元）")
    suggested_price = Column(Float, nullable=True, comment="建议售价（元）")
    gross_margin = Column(Float, nullable=True, comment="毛利率（%）")

    # 营养成分表
    nutrition_info = Column(Text, nullable=True, comment="营养成分数据（JSON 格式）")

    # 过敏原信息
    allergen_info = Column(Text, nullable=True, comment="过敏原信息（JSON 格式）")

    # 保质期与储存
    shelf_life_days = Column(Integer, nullable=True, comment="保质期天数")
    storage_temperature = Column(String(50), nullable=True, comment="储存温度要求")

    # 版本控制
    version = Column(Integer, default=1, nullable=False, comment="版本号")
    is_latest = Column(Boolean, default=True, nullable=False, index=True, comment="是否为最新版本")

    # 审计字段
    created_by = Column(String(36), nullable=False, comment="创建人 ID")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # 关联关系
    recipe = relationship("Recipe", back_populates="standard_recipes")
    enterprise = relationship("Enterprise", back_populates="standard_recipes")
