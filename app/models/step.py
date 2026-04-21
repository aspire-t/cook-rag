"""RecipeStep 模型 - 菜谱步骤表."""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from . import Base


class RecipeStep(Base):
    """菜谱 - 步骤表."""

    __tablename__ = "recipe_steps"

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

    step_no: Mapped[int] = mapped_column(Integer, nullable=False)  # 步骤序号
    description: Mapped[str] = mapped_column(nullable=False)  # 步骤描述
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 预估耗时（秒）
    tips: Mapped[str | None] = mapped_column(nullable=True)  # 小贴士
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 步骤图片 URL（MVP 后可选）

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # 关联
    recipe: Mapped["Recipe"] = relationship(back_populates="steps")

    __table_args__ = (
        UniqueConstraint("recipe_id", "step_no", name="idx_recipe_steps_unique"),
    )

    def __repr__(self) -> str:
        return f"<RecipeStep(id={self.id}, recipe_id={self.recipe_id}, step_no={self.step_no})>"
