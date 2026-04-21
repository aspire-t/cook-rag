"""搜索历史模型."""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models import Base


class SearchHistory(Base):
    """搜索历史记录."""

    __tablename__ = "search_history"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    session_id = Column(String(64), nullable=True, index=True)  # 匿名用户 session_id

    # 搜索信息
    query = Column(String(512), nullable=False)
    filters = Column(String(2048))  # JSON 格式存储过滤条件

    # 结果信息
    result_count = Column(Integer, default=0)
    clicked_recipe_id = Column(String(36), nullable=True)  # 点击的菜谱 ID

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 索引
    __table_args__ = (
        Index("idx_user_created", "user_id", "created_at"),
        Index("idx_session_created", "session_id", "created_at"),
    )

    def __repr__(self):
        return f"<SearchHistory(id={self.id}, user_id={self.user_id}, query={self.query})>"
