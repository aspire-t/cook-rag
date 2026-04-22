"""举报数据模型."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from . import Base

if TYPE_CHECKING:
    from .recipe import Recipe
    from .user import User


class Report(Base):
    """菜谱举报模型."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, comment="举报原因")
    status: Mapped[str | None] = mapped_column(
        String(32),
        default="pending",
        nullable=True,
        comment="举报状态：pending/processed",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # 关联关系
    recipe: Mapped["Recipe"] = relationship(back_populates="reports")
    user: Mapped["User"] = relationship()

    __table_args__ = (
        Index("idx_reports_recipe_user", "recipe_id", "user_id"),
    )

    def __repr__(self):
        return f"<Report(id={self.id}, recipe_id={self.recipe_id}, status={self.status})>"
