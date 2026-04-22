"""RecipeImage 模型 - 图片元数据."""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from . import Base


class RecipeImage(Base):
    """菜谱图片模型."""

    __tablename__ = "recipe_images"

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
    step_no: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 步骤编号，封面图为 None
    image_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "cover" 或 "step"
    source_path: Mapped[str] = mapped_column(String(500), nullable=False)  # 原始路径（king-jingxiang/HowToCook）
    local_path: Mapped[str] = mapped_column(String(500), nullable=False)  # 本地存储路径
    image_url: Mapped[str] = mapped_column(String(1000), nullable=False)  # CDN URL
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 图片宽度
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 图片高度
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 文件大小（字节）
    clip_vector_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Qdrant 中的向量 ID

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # 关联关系
    recipe: Mapped["Recipe"] = relationship(back_populates="images")

    def __repr__(self) -> str:
        return f"<RecipeImage(id={self.id}, recipe_id={self.recipe_id}, image_type={self.image_type})>"
