"""Favorite 模型 - 用户收藏表."""

from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, PrimaryKeyConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from . import Base


class Favorite(Base):
    """用户收藏表."""

    __tablename__ = "favorites"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # 关联
    user: Mapped["User"] = relationship(back_populates="favorites")
    recipe: Mapped["Recipe"] = relationship(back_populates="favorites")

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "recipe_id", name="favorites_pkey"),
        Index("idx_favorites_user", "user_id"),
        Index("idx_favorites_recipe", "recipe_id"),
    )

    def __repr__(self) -> str:
        return f"<Favorite(user_id={self.user_id}, recipe_id={self.recipe_id})>"
