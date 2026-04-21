"""举报数据模型."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import relationship
from . import Base


class Report(Base):
    """菜谱举报模型."""

    __tablename__ = "reports"

    id = Column(String(36), primary_key=True)
    recipe_id = Column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason = Column(String(1024), nullable=False, comment="举报原因")
    status = Column(String(32), default="pending", comment="举报状态：pending/processed")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 关联关系
    recipe = relationship("Recipe", back_populates="reports")
    user = relationship("User")

    def __repr__(self):
        return f"<Report(id={self.id}, recipe_id={self.recipe_id}, status={self.status})>"
