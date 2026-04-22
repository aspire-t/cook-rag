"""搜索历史模型."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from . import Base

if TYPE_CHECKING:
    from .user import User


class SearchHistory(Base):
    """搜索历史记录."""

    __tablename__ = "search_histories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # 关联用户 (可选，匿名用户为 NULL)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # 匿名用户 session_id
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # 搜索信息
    query: Mapped[str] = mapped_column(Text, nullable=False, comment="搜索关键词")
    filters: Mapped[str | None] = mapped_column(Text, nullable=True, comment="过滤条件 (JSON 格式)")

    # 结果信息
    result_count: Mapped[int] = mapped_column(Integer, default=0, comment="搜索结果数量")
    clicked_recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="点击的菜谱 ID",
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # 关联关系
    user: Mapped["User"] = relationship(back_populates="search_histories")

    __table_args__ = (
        Index("idx_search_histories_user_created", "user_id", "created_at"),
        Index("idx_search_histories_session_created", "session_id", "created_at"),
    )

    def __repr__(self):
        return f"<SearchHistory(id={self.id}, user_id={self.user_id}, query={self.query})>"
