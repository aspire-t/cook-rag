"""RecipeIngredient 模型 - 菜谱食材表."""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from . import Base


class RecipeIngredient(Base):
    """菜谱 - 食材表."""

    __tablename__ = "recipe_ingredients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 食材名称
    amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)  # 用量
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 单位 (g/ml/个/勺...)
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 排序序号
    notes: Mapped[str | None] = mapped_column(nullable=True)  # 备注（如"切块"、"去皮"）

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # 关联
    recipe: Mapped["Recipe"] = relationship(back_populates="ingredients")

    __table_args__ = (
        UniqueConstraint("recipe_id", "name", "sequence", name="idx_recipe_ingredients_unique"),
    )

    def __repr__(self) -> str:
        return f"<RecipeIngredient(id={self.id}, recipe_id={self.recipe_id}, name={self.name})>"
