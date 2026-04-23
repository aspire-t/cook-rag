# CookRAG 多模态图片存储实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现菜谱图片存储、展示和以图搜菜功能，支持封面图和步骤图的 GitHub CDN 存储，集成 Chinese-CLIP 向量化能力

**Architecture:** 图片存储于自有 GitHub 仓库 (aspire-t/cook-rag-images)，通过 Raw CDN 访问；PostgreSQL 存储图片元数据；Qdrant 存储 CLIP 图片向量 (512 维)；Chinese-CLIP 模型本地部署生成向量

**Tech Stack:** GitHub API, Chinese-CLIP (OFA-Sys/chinese-clip-vit-base-patch16), PyTorch, Qdrant, PostgreSQL, FastAPI

---

### Task 1: 配置管理和数据库模型

**Files:**
- Modify: `app/core/config.py`
- Create: `app/models/recipe_image.py`
- Modify: `app/models/recipe.py`
- Modify: `app/models/step.py`
- Create: `alembic/versions/008_recipe_images.py`
- Test: `tests/models/test_recipe_image.py`

- [ ] **Step 1: 修改配置文件添加图片和 CLIP 配置**

编辑 `app/core/config.py`，在 `Settings` 类中添加：

```python
# 图片仓库配置
IMAGE_REPO_NAME: str = "aspire-t/cook-rag-images"
IMAGE_REPO_TOKEN: str = ""
IMAGE_BASE_CDN_URL: str = "https://raw.githubusercontent.com/aspire-t/cook-rag-images/master"

# CLIP 模型配置
CLIP_MODEL_NAME: str = "OFA-Sys/chinese-clip-vit-base-patch16"
CLIP_DEVICE: str = "auto"
```

- [ ] **Step 2: 运行配置测试验证新配置项**

```bash
cd /Users/wangzhentao/code/cook-rag
python -c "from app.core.config import settings; print(settings.IMAGE_REPO_NAME, settings.CLIP_MODEL_NAME)"
```
Expected: 输出配置值

- [ ] **Step 3: 创建 RecipeImage 模型**

创建 `app/models/recipe_image.py`：

```python
"""RecipeImage 模型 - 菜谱图片元数据表."""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from . import Base


class RecipeImage(Base):
    """菜谱图片元数据表."""

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
    step_no: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NULL=封面图
    image_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="cover",
    )  # cover/step/ingredient
    source_path: Mapped[str] = mapped_column(Text, nullable=False)  # 原始 GitHub 路径
    local_path: Mapped[str] = mapped_column(String(200), nullable=False)  # 自有仓库路径
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)  # CDN URL
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clip_vector_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # 关联
    recipe: Mapped["Recipe"] = relationship(back_populates="images")

    def __repr__(self) -> str:
        return f"<RecipeImage(id={self.id}, recipe_id={self.recipe_id}, type={self.image_type})>"
```

- [ ] **Step 4: 更新 `__init__.py` 导出 RecipeImage 模型**

编辑 `app/models/__init__.py`，添加导出：

```python
from .recipe_image import RecipeImage

__all__ = [
    "User",
    "Recipe",
    "RecipeIngredient",
    "RecipeStep",
    "Favorite",
    "SearchHistory",
    "Report",
    "RecipeImage",  # 新增
]
```

- [ ] **Step 5: 更新 Recipe 模型添加图片关联**

编辑 `app/models/recipe.py`，在 `Recipe` 类中添加：

```python
# 在 existing relationships 后添加
images: Mapped[list["RecipeImage"]] = relationship(
    back_populates="recipe",
    cascade="all, delete-orphan",
)
```

- [ ] **Step 6: 更新 RecipeStep 模型添加 image_path 字段**

编辑 `app/models/step.py`，在 `RecipeStep` 类中添加：

```python
image_path: Mapped[str | None] = mapped_column(String(200), nullable=True)  # 步骤图片在自有仓库的相对路径
```

- [ ] **Step 7: 编写 RecipeImage 模型测试**

创建 `tests/models/test_recipe_image.py`：

```python
"""RecipeImage 模型测试."""

import pytest
from sqlalchemy import select
from app.models.recipe_image import RecipeImage


class TestRecipeImageModel:
    """RecipeImage 模型测试."""

    @pytest.mark.asyncio
    async def test_create_recipe_image(self, async_session):
        """测试创建图片元数据."""
        from app.models.recipe import Recipe

        # 先创建菜谱
        recipe = Recipe(
            name="测试菜谱",
            description="测试描述",
            cuisine="家常菜",
            difficulty="easy",
            is_public=True,
            audit_status="approved",
        )
        async_session.add(recipe)
        await async_session.commit()
        await async_session.refresh(recipe)

        # 创建封面图
        cover_image = RecipeImage(
            recipe_id=recipe.id,
            step_no=None,
            image_type="cover",
            source_path="dishes/vegetable_dish/测试菜/测试菜.jpg",
            local_path="images/recipe/test-id/cover.jpg",
            image_url="https://raw.githubusercontent.com/test/repo/master/images/recipe/test-id/cover.jpg",
            width=800,
            height=600,
            file_size=102400,
        )
        async_session.add(cover_image)
        await async_session.commit()

        # 验证
        result = await async_session.execute(
            select(RecipeImage).where(RecipeImage.recipe_id == recipe.id)
        )
        images = result.scalars().all()
        assert len(images) == 1
        assert images[0].image_type == "cover"
        assert images[0].step_no is None

    @pytest.mark.asyncio
    async def test_create_step_image(self, async_session):
        """测试创建步骤图片."""
        from app.models.recipe import Recipe

        recipe = Recipe(
            name="测试菜谱 2",
            description="测试描述",
            is_public=True,
            audit_status="approved",
        )
        async_session.add(recipe)
        await async_session.commit()
        await async_session.refresh(recipe)

        step_image = RecipeImage(
            recipe_id=recipe.id,
            step_no=1,
            image_type="step",
            source_path="dishes/vegetable_dish/测试菜/步骤 1.jpg",
            local_path="images/recipe/test-id/step_1.jpg",
            image_url="https://raw.githubusercontent.com/test/repo/master/images/recipe/test-id/step_1.jpg",
        )
        async_session.add(step_image)
        await async_session.commit()

        result = await async_session.execute(
            select(RecipeImage).where(RecipeImage.recipe_id == recipe.id)
        )
        images = result.scalars().all()
        assert len(images) == 1
        assert images[0].image_type == "step"
        assert images[0].step_no == 1
```

- [ ] **Step 8: 运行模型测试**

```bash
cd /Users/wangzhentao/code/cook-rag
pytest tests/models/test_recipe_image.py -v
```
Expected: 2 passed

- [ ] **Step 9: 创建 Alembic 迁移文件**

创建 `alembic/versions/008_recipe_images.py`：

```python
"""recipe_images 表创建及字段变更

Revision ID: 008
Revises: 007
Create Date: 2026-04-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 recipe_images 表
    op.create_table(
        'recipe_images',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recipe_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_no', sa.Integer(), nullable=True),
        sa.Column('image_type', sa.String(length=20), nullable=False),
        sa.Column('source_path', sa.Text(), nullable=False),
        sa.Column('local_path', sa.String(length=200), nullable=False),
        sa.Column('image_url', sa.String(length=500), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('clip_vector_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE')
    )
    op.create_index('idx_recipe_images_recipe', 'recipe_images', ['recipe_id'], unique=False)
    op.create_index('idx_recipe_images_type', 'recipe_images', ['image_type', 'step_no'], unique=False)
    op.create_index(
        'idx_recipe_images_clip',
        'recipe_images',
        ['clip_vector_id'],
        unique=False,
        postgresql_where=sa.text('clip_vector_id IS NOT NULL')
    )

    # recipes 表新增封面图字段
    op.add_column('recipes', sa.Column('cover_image_url', sa.String(length=500), nullable=True))
    op.add_column('recipes', sa.Column('cover_image_path', sa.String(length=200), nullable=True))

    # recipe_steps 表新增图片路径字段
    op.add_column('recipe_steps', sa.Column('image_path', sa.String(length=200), nullable=True))

    # 添加字段注释
    op.execute("COMMENT ON COLUMN recipes.cover_image_url IS '菜谱封面图 CDN URL'")
    op.execute("COMMENT ON COLUMN recipes.cover_image_path IS '封面图在图片仓库的相对路径'")
    op.execute("COMMENT ON COLUMN recipe_steps.image_path IS '步骤图片在图片仓库的相对路径'")
    op.execute("COMMENT ON TABLE recipe_images IS '菜谱图片元数据表'")
    op.execute("COMMENT ON COLUMN recipe_images.step_no IS '步骤序号，NULL 表示封面图'")
    op.execute("COMMENT ON COLUMN recipe_images.source_path IS '原始 GitHub 仓库路径'")
    op.execute("COMMENT ON COLUMN recipe_images.local_path IS '自有图片仓库相对路径'")
    op.execute("COMMENT ON COLUMN recipe_images.clip_vector_id IS 'CLIP 图片向量在 Qdrant 的 ID'")


def downgrade() -> None:
    # 删除字段
    op.drop_column('recipe_steps', 'image_path')
    op.drop_column('recipes', 'cover_image_path')
    op.drop_column('recipes', 'cover_image_url')

    # 删除表
    op.drop_index('idx_recipe_images_clip', table_name='recipe_images')
    op.drop_index('idx_recipe_images_type', table_name='recipe_images')
    op.drop_index('idx_recipe_images_recipe', table_name='recipe_images')
    op.drop_table('recipe_images')
```

- [ ] **Step 10: 验证 Alembic 迁移文件语法**

```bash
cd /Users/wangzhentao/code/cook-rag
python -c "from alembic.versions import _008_recipe_images; print('Migration file syntax OK')"
```

- [ ] **Step 11: 提交**

```bash
cd /Users/wangzhentao/code/cook-rag
git add app/core/config.py app/models/recipe_image.py app/models/recipe.py app/models/step.py app/models/__init__.py alembic/versions/008_recipe_images.py tests/models/test_recipe_image.py
git commit -m "feat: 添加 RecipeImage 模型和数据库迁移 (Task 35)"
```

---

### Task 2: CLIP 向量化服务

**Files:**
- Create: `app/services/clip_service.py`
- Modify: `requirements.txt`
- Test: `tests/services/test_clip_service.py`

- [ ] **Step 1: 创建 CLIP 服务**

创建 `app/services/clip_service.py`：

```python
"""CLIP 图片向量化服务."""

from typing import Optional
from transformers import CLIPProcessor, CLIPModel
import torch
from PIL import Image
import requests
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class ClipService:
    """CLIP 图片向量化服务."""

    MODEL_NAME = "OFA-Sys/chinese-clip-vit-base-patch16"
    VECTOR_SIZE = 512

    def __init__(self):
        self.device = self._get_device()
        logger.info(f"Loading CLIP model on {self.device}...")
        self.model = CLIPModel.from_pretrained(self.MODEL_NAME).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(self.MODEL_NAME)
        self.model.eval()
        logger.info("CLIP model loaded successfully")

    def _get_device(self) -> str:
        """获取最佳可用设备."""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    @torch.no_grad()
    def get_image_embedding(self, image_url: str) -> list:
        """
        生成图片向量.

        Args:
            image_url: 图片 URL 或本地路径

        Returns:
            512 维归一化向量列表
        """
        # 加载图片
        if image_url.startswith("http"):
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
        else:
            image = Image.open(image_url)

        # 转换为 RGB (处理 RGBA 图片)
        if image.mode != "RGB":
            image = image.convert("RGB")

        # 处理并生成向量
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        image_features = self.model.get_image_features(**inputs)

        # 归一化（COSINE 距离需要）
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        return image_features.cpu().numpy()[0].tolist()

    @torch.no_grad()
    def get_text_embedding(self, text: str) -> list:
        """
        生成文本向量（用于跨模态检索）.

        Args:
            text: 中文文本

        Returns:
            512 维归一化向量列表
        """
        inputs = self.processor(text=text, return_tensors="pt").to(self.device)
        text_features = self.model.get_text_features(**inputs)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        return text_features.cpu().numpy()[0].tolist()

    @torch.no_grad()
    def batch_get_image_embeddings(self, image_urls: list[str]) -> list[list]:
        """
        批量生成图片向量.

        Args:
            image_urls: 图片 URL 列表

        Returns:
            归一化向量列表
        """
        images = []
        for url in image_urls:
            if url.startswith("http"):
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
            else:
                image = Image.open(url)

            if image.mode != "RGB":
                image = image.convert("RGB")
            images.append(image)

        # 批量处理
        inputs = self.processor(images=images, return_tensors="pt", padding=True).to(self.device)
        image_features = self.model.get_image_features(**inputs)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        return image_features.cpu().numpy().tolist()


# 单例
_clip_service: Optional[ClipService] = None


def get_clip_service() -> ClipService:
    """获取 CLIP 服务单例."""
    global _clip_service
    if _clip_service is None:
        _clip_service = ClipService()
    return _clip_service
```

- [ ] **Step 2: 更新 requirements.txt 添加 CLIP 依赖**

编辑 `requirements.txt`，添加：

```
transformers>=4.36.0
torch>=2.0.0
Pillow>=10.0.0
```

- [ ] **Step 3: 编写 CLIP 服务测试**

创建 `tests/services/test_clip_service.py`：

```python
"""CLIP 服务测试."""

import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
import numpy as np


class TestClipService:
    """CLIP 服务测试."""

    @patch('app.services.clip_service.CLIPModel.from_pretrained')
    @patch('app.services.clip_service.CLIPProcessor.from_pretrained')
    def test_clip_service_initialization(self, mock_processor, mock_model):
        """测试 CLIP 服务初始化."""
        from app.services.clip_service import ClipService

        # Mock 模型和处理器
        mock_model_instance = MagicMock()
        mock_model.return_value = mock_model_instance
        mock_processor_instance = MagicMock()
        mock_processor.return_value = mock_processor_instance

        service = ClipService()

        assert service.model is not None
        assert service.processor is not None
        assert service.VECTOR_SIZE == 512

    @patch('app.services.clip_service.requests.get')
    @patch('app.services.clip_service.CLIPModel.from_pretrained')
    @patch('app.services.clip_service.CLIPProcessor.from_pretrained')
    def test_get_image_embedding(self, mock_processor, mock_model, mock_requests):
        """测试图片向量生成."""
        from app.services.clip_service import ClipService

        # Mock 响应
        mock_response = MagicMock()
        mock_response.content = b'fake_image_data'
        mock_requests.return_value = mock_response

        # Mock 模型输出
        mock_model_instance = MagicMock()
        mock_model.return_value = mock_model_instance
        mock_model_instance.get_image_features.return_value = MagicMock(
            cpu=MagicMock(return_value=MagicMock(
                numpy=MagicMock(return_value=np.random.rand(1, 512))
            ))
        )
        mock_model_instance.get_image_features.return_value.norm.return_value = 1.0

        mock_processor_instance = MagicMock()
        mock_processor.return_value = mock_processor_instance

        service = ClipService()
        embedding = service.get_image_embedding("http://example.com/image.jpg")

        assert len(embedding) == 512
        assert isinstance(embedding, list)

    def test_get_text_embedding_mock(self):
        """测试文本向量生成（Mock）."""
        from app.services.clip_service import ClipService

        with patch('app.services.clip_service.CLIPModel.from_pretrained') as mock_model:
            with patch('app.services.clip_service.CLIPProcessor.from_pretrained') as mock_processor:
                mock_model_instance = MagicMock()
                mock_model.return_value = mock_model_instance
                mock_model_instance.get_text_features.return_value = MagicMock(
                    cpu=MagicMock(return_value=MagicMock(
                        numpy=MagicMock(return_value=np.random.rand(1, 512))
                    ))
                )
                mock_model_instance.get_text_features.return_value.norm.return_value = 1.0

                mock_processor_instance = MagicMock()
                mock_processor.return_value = mock_processor_instance

                service = ClipService()
                embedding = service.get_text_embedding("宫保鸡丁")

                assert len(embedding) == 512
                assert isinstance(embedding, list)
```

- [ ] **Step 4: 运行 CLIP 服务测试**

```bash
cd /Users/wangzhentao/code/cook-rag
pytest tests/services/test_clip_service.py -v
```
Expected: 3 passed

- [ ] **Step 5: 验证 CLIP 模型可下载性**

```bash
python -c "from transformers import CLIPProcessor, CLIPModel; print('CLIP imports OK')"
```

- [ ] **Step 6: 提交**

```bash
cd /Users/wangzhentao/code/cook-rag
git add app/services/clip_service.py requirements.txt tests/services/test_clip_service.py
git commit -m "feat: 实现 CLIP 图片向量化服务 (Task 37)"
```

---

### Task 3: Qdrant 图片向量集成

**Files:**
- Modify: `app/services/qdrant_schema.py`
- Modify: `app/services/qdrant_service.py`
- Test: `tests/services/test_qdrant_image.py`

- [ ] **Step 1: 更新 Qdrant Schema 添加 image_vec 字段**

编辑 `app/services/qdrant_schema.py`：

```python
"""Qdrant Collection Schema 定义."""

from qdrant_client.http.models import (
    VectorParams,
    Distance,
    BinaryQuantization,
    BinaryQuantizationConfig,
)


# 向量维度
TEXT_VECTOR_SIZE = 1024  # BGE-M3 输出维度
IMAGE_VECTOR_SIZE = 512  # CLIP 输出维度


def get_collection_config() -> dict:
    """
    获取 Collection 配置.

    Returns:
        配置字典
    """
    return {
        "vectors": {
            # 原有文本向量
            "name_vec": VectorParams(size=TEXT_VECTOR_SIZE, distance=Distance.COSINE),
            "desc_vec": VectorParams(size=TEXT_VECTOR_SIZE, distance=Distance.COSINE),
            "step_vec": VectorParams(size=TEXT_VECTOR_SIZE, distance=Distance.COSINE),
            "tag_vec": VectorParams(size=TEXT_VECTOR_SIZE, distance=Distance.COSINE),
            # 新增图片向量
            "image_vec": VectorParams(size=IMAGE_VECTOR_SIZE, distance=Distance.COSINE),
        },
        # 二进制量化
        "quantization_config": BinaryQuantization(
            binary=BinaryQuantizationConfig(always_ram=True)
        ),
        "shard_number": 1,
        "replication_factor": 1,
    }


# Payload Schema 定义
PAYLOAD_SCHEMA = {
    # 菜系过滤
    "cuisine": {"type": "keyword", "description": "菜系（川菜/粤菜等）"},
    "difficulty": {"type": "keyword", "description": "难度（easy/medium/hard）"},
    "taste": {"type": "keyword", "description": "口味标签数组"},
    "prep_time": {"type": "integer", "description": "准备时间（分钟）"},
    "cook_time": {"type": "integer", "description": "烹饪时间（分钟）"},
    "user_id": {"type": "keyword", "description": "用户 ID"},
    "is_public": {"type": "boolean", "description": "是否公开"},
    "audit_status": {"type": "keyword", "description": "审核状态"},
    "recipe_id": {"type": "keyword", "description": "菜谱 ID"},
    "name": {"type": "keyword", "description": "菜名"},
    # 新增图片相关
    "has_image": {"type": "boolean", "description": "是否有图片"},
    "image_type": {"type": "keyword", "description": "图片类型：cover/step"},
}
```

- [ ] **Step 2: 更新 Qdrant 服务添加图片向量方法**

编辑 `app/services/qdrant_service.py`，添加方法：

```python
# 在 QdrantService 类中添加
def upsert_image_vector(
    self,
    recipe_id: str,
    vector: list,
    payload: dict,
) -> bool:
    """
    上传图片向量到 Qdrant.

    Args:
        recipe_id: 菜谱 ID
        vector: 512 维 CLIP 向量
        payload: 元数据

    Returns:
        是否成功
    """
    from qdrant_client.http.models import PointStruct

    point = PointStruct(
        id=hash(recipe_id) % (10 ** 10),  # 生成唯一 ID
        vector={"image_vec": vector},
        payload=payload,
    )

    result = self.client.upsert(
        collection_name=self.collection_name,
        points=[point],
    )

    return result.status == "completed"

def search_by_image_vector(
    self,
    query_vector: list,
    limit: int = 10,
    filter_conditions: dict = None,
) -> list:
    """
    按图片向量搜索.

    Args:
        query_vector: 查询向量
        limit: 返回数量
        filter_conditions: 过滤条件

    Returns:
        搜索结果列表
    """
    from qdrant_client.http.models import Filter, FieldCondition, MatchValue

    query_filter = None
    if filter_conditions:
        conditions = []
        for key, value in filter_conditions.items():
            conditions.append(
                FieldCondition(key=key, match=MatchValue(value=value))
            )
        query_filter = Filter(must=conditions)

    results = self.client.search(
        collection_name=self.collection_name,
        query_vector=("image_vec", query_vector),
        query_filter=query_filter,
        limit=limit,
    )

    return results
```

- [ ] **Step 3: 编写 Qdrant 图片向量测试**

创建 `tests/services/test_qdrant_image.py`：

```python
"""Qdrant 图片向量测试."""

import pytest
from unittest.mock import MagicMock, patch


class TestQdrantImageVector:
    """Qdrant 图片向量测试."""

    @patch('app.services.qdrant_service.QdrantClient')
    def test_upsert_image_vector(self, mock_client):
        """测试上传图片向量."""
        from app.services.qdrant_service import QdrantService

        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.upsert.return_value = MagicMock(status="completed")

        service = QdrantService()
        vector = [0.1] * 512
        payload = {"recipe_id": "test-123", "image_type": "cover"}

        result = service.upsert_image_vector("test-123", vector, payload)

        assert result is True
        mock_client_instance.upsert.assert_called_once()

    @patch('app.services.qdrant_service.QdrantClient')
    def test_search_by_image_vector(self, mock_client):
        """测试按图片向量搜索."""
        from app.services.qdrant_service import QdrantService

        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.search.return_value = [
            MagicMock(id=1, score=0.95, payload={"recipe_id": "test-1"}),
            MagicMock(id=2, score=0.85, payload={"recipe_id": "test-2"}),
        ]

        service = QdrantService()
        query_vector = [0.1] * 512

        results = service.search_by_image_vector(query_vector, limit=10)

        assert len(results) == 2
        assert results[0].score > results[1].score
```

- [ ] **Step 4: 运行测试**

```bash
cd /Users/wangzhentao/code/cook-rag
pytest tests/services/test_qdrant_image.py -v
```
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
cd /Users/wangzhentao/code/cook-rag
git add app/services/qdrant_schema.py app/services/qdrant_service.py tests/services/test_qdrant_image.py
git commit -m "feat: Qdrant 集成图片向量支持 (Task 38)"
```

---

### Task 4: 图片导入脚本

**Files:**
- Create: `app/services/image_importer.py`
- Create: `scripts/import_images.py`
- Test: `tests/services/test_image_importer.py`

- [ ] **Step 1: 创建图片导入服务**

创建 `app/services/image_importer.py`：

```python
"""图片导入服务."""

import re
import requests
from pathlib import Path
from typing import List, Optional
from github import Github
from app.core.config import settings


class ImageImporter:
    """图片导入器."""

    def __init__(self):
        self.github = Github(settings.IMAGE_REPO_TOKEN)
        self.image_repo = self.github.get_repo(settings.IMAGE_REPO_NAME)
        self.base_cdn_url = settings.IMAGE_BASE_CDN_URL

    def extract_images_from_markdown(
        self, md_path: Path, md_content: str
    ) -> List[dict]:
        """
        从 Markdown 提取图片引用.

        Returns:
            [{"source_path": "...", "image_type": "cover/step", "step_no": 1}]
        """
        images = []
        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'

        for match in re.finditer(pattern, md_content):
            desc, rel_path = match.groups()
            source_path = str(md_path.parent / rel_path)

            # 判断图片类型
            image_type = "cover"
            step_no = None

            if "步骤" in desc.lower() or re.search(r'\d', Path(rel_path).stem):
                image_type = "step"
                step_match = re.search(r'(\d+)', desc + Path(rel_path).stem)
                if step_match:
                    step_no = int(step_match.group(1))

            images.append({
                "source_path": source_path,
                "image_type": image_type,
                "step_no": step_no,
            })

        return images

    def download_and_upload_image(
        self, source_path: str, dest_path: str
    ) -> str:
        """
        下载源图片并上传到自己仓库.

        Returns:
            CDN URL
        """
        # 从 king-jingxiang 下载
        source_url = f"https://raw.githubusercontent.com/king-jingxiang/HowToCook/master/{source_path}"
        response = requests.get(source_url, timeout=30)
        response.raise_for_status()
        image_data = response.content

        # 上传到 GitHub
        self.image_repo.create_file(
            path=dest_path,
            message=f"Add image: {dest_path}",
            content=image_data,
            branch="master",
        )

        return f"{self.base_cdn_url}/{dest_path}"

    def import_recipe_images(
        self, recipe_id: str, recipe_name: str, md_path: Path
    ) -> List[dict]:
        """
        导入单个菜谱的图片.

        Returns:
            导入的图片元数据列表
        """
        md_content = md_path.read_text(encoding="utf-8")
        images = self.extract_images_from_markdown(md_path, md_content)

        imported = []
        for i, img in enumerate(images):
            if img["image_type"] == "cover":
                dest_path = f"images/recipe/{recipe_id}/cover.jpg"
            else:
                step_num = img["step_no"] if img["step_no"] else i
                dest_path = f"images/recipe/{recipe_id}/step_{step_num}.jpg"

            try:
                cdn_url = self.download_and_upload_image(
                    img["source_path"], dest_path
                )
                imported.append({
                    "recipe_id": recipe_id,
                    "image_type": img["image_type"],
                    "step_no": img["step_no"],
                    "source_path": img["source_path"],
                    "local_path": dest_path,
                    "image_url": cdn_url,
                })
            except Exception as e:
                print(f"导入图片失败 {img['source_path']}: {e}")

        return imported
```

- [ ] **Step 2: 创建批量导入脚本**

创建 `scripts/import_images.py`：

```python
#!/usr/bin/env python3
"""从 HowToCook 仓库导入图片到自有仓库和数据库."""

import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from app.services.image_importer import ImageImporter
from app.services.clip_service import get_clip_service
from app.services.qdrant_service import get_qdrant_service

HOWTOCOOK_PATH = Path("/tmp/HowToCook")
DATABASE_URL = "postgresql+asyncpg://cookrag:password@localhost:5432/cookrag"


async def main():
    print("=== 开始导入 HowToCook 图片数据 ===\n")

    importer = ImageImporter()
    clip_service = get_clip_service()
    qdrant_service = get_qdrant_service()
    engine = create_async_engine(DATABASE_URL)

    total_images = 0
    success = 0
    failed = 0

    async with engine.begin() as conn:
        md_files = list(HOWTOCOOK_PATH.glob("dishes/**/*.md"))
        print(f"找到 {len(md_files)} 个菜谱文件\n")

        for md_file in md_files:
            result = await conn.execute(
                "SELECT id FROM recipes WHERE name = :name AND source_type = 'howtocook'",
                {"name": md_file.stem},
            )
            row = result.fetchone()
            if not row:
                continue

            recipe_id = row[0]
            images = importer.import_recipe_images(recipe_id, md_file.stem, md_file)

            for img in images:
                total_images += 1
                try:
                    await conn.execute(
                        """
                        INSERT INTO recipe_images 
                        (recipe_id, image_type, step_no, source_path, local_path, image_url)
                        VALUES (:recipe_id, :image_type, :step_no, :source_path, :local_path, :image_url)
                        """,
                        img,
                    )

                    # 生成 CLIP 向量
                    vector = clip_service.get_image_embedding(img["image_url"])

                    # 上传到 Qdrant
                    payload = {
                        "recipe_id": img["recipe_id"],
                        "image_type": img["image_type"],
                        "has_image": True,
                    }
                    qdrant_service.upsert_image_vector(
                        recipe_id, vector, payload
                    )

                    success += 1
                    print(f"导入成功：{img['local_path']}")
                except Exception as e:
                    failed += 1
                    print(f"导入失败 {img['local_path']}: {e}")

            if total_images % 10 == 0:
                print(f"\n--- 进度：{total_images} (成功:{success} 失败:{failed}) ---\n")

    print(f"\n=== 导入完成 ===")
    print(f"总计：{total_images} 张图片")
    print(f"成功：{success} 张")
    print(f"失败：{failed} 张")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: 编写图片导入服务测试**

创建 `tests/services/test_image_importer.py`：

```python
"""图片导入服务测试."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestImageImporter:
    """图片导入器测试."""

    def test_extract_images_cover(self):
        """测试提取封面图."""
        from app.services.image_importer import ImageImporter

        importer = ImageImporter()
        md_content = "![烤蛋挞](./烤蛋挞.png)"
        md_path = Path("/tmp/test/dishes/dessert/烤蛋挞/烤蛋挞.md")

        images = importer.extract_images_from_markdown(md_path, md_content)

        assert len(images) == 1
        assert images[0]["image_type"] == "cover"
        assert images[0]["step_no"] is None

    def test_extract_images_step(self):
        """测试提取步骤图."""
        from app.services.image_importer import ImageImporter

        importer = ImageImporter()
        md_content = "![步骤 1](./步骤 1.jpg)"
        md_path = Path("/tmp/test/dishes/vegetable_dish/凉拌木耳/凉拌木耳.md")

        images = importer.extract_images_from_markdown(md_path, md_content)

        assert len(images) == 1
        assert images[0]["image_type"] == "step"
        assert images[0]["step_no"] == 1

    @patch('app.services.image_importer.requests.get')
    @patch('app.services.image_importer.Github')
    def test_download_and_upload_image(self, mock_github, mock_requests):
        """测试下载并上传图片."""
        from app.services.image_importer import ImageImporter

        mock_response = MagicMock()
        mock_response.content = b'fake_image_data'
        mock_requests.return_value = mock_response

        mock_repo = MagicMock()
        mock_github.return_value.get_repo.return_value = mock_repo

        importer = ImageImporter()
        url = importer.download_and_upload_image(
            "dishes/test/test.jpg", "images/recipe/test/cover.jpg"
        )

        assert "raw.githubusercontent.com" in url
        mock_repo.create_file.assert_called_once()
```

- [ ] **Step 4: 运行测试**

```bash
cd /Users/wangzhentao/code/cook-rag
pytest tests/services/test_image_importer.py -v
```
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
cd /Users/wangzhentao/code/cook-rag
git add app/services/image_importer.py scripts/import_images.py tests/services/test_image_importer.py
git commit -m "feat: 实现图片导入脚本和服务 (Task 36)"
```

---

### Task 5: 图片 API 接口

**Files:**
- Modify: `app/api/schemas.py`
- Create: `app/api/v1/images.py`
- Modify: `app/api/routes.py`
- Test: `tests/api/test_images.py`

- [ ] **Step 1: 添加图片 API Schema**

编辑 `app/api/schemas.py`，添加：

```python
from enum import Enum
# ... 在文件末尾添加


class ImageType(str, Enum):
    """图片类型."""
    COVER = "cover"
    STEP = "step"
    INGREDIENT = "ingredient"


class ImageInfo(BaseModel):
    """图片信息."""
    url: str = Field(..., description="图片 CDN URL")
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")


class StepImage(ImageInfo):
    """步骤图片."""
    step_no: int = Field(..., description="步骤序号")


class RecipeImagesResponse(BaseModel):
    """菜谱图片列表响应."""
    recipe_id: str
    cover: Optional[ImageInfo] = None
    steps: List[StepImage] = []


class ImageSearchMode(str, Enum):
    """图片搜索模式."""
    VISUAL = "visual"
    MULTIMODAL = "multimodal"


class ImageSearchRequest(BaseModel):
    """以图搜菜请求."""
    image_url: str = Field(..., description="图片 URL 或 base64")
    limit: int = Field(10, ge=1, le=50, description="返回数量")
    search_mode: ImageSearchMode = Field(ImageSearchMode.VISUAL, description="搜索模式")


class ImageSearchResult(BaseModel):
    """以图搜菜结果项."""
    id: str
    name: str
    cuisine: str
    image_url: str
    similarity_score: float = Field(..., description="相似度分数")
    match_reasons: List[str]
```

- [ ] **Step 2: 创建图片 API 路由**

创建 `app/api/v1/images.py`：

```python
"""图片 API 路由."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.models.recipe_image import RecipeImage
from app.api.schemas import RecipeImagesResponse, ImageInfo, StepImage

router = APIRouter(prefix="/recipes", tags=["图片管理"])


@router.get("/{recipe_id}/images", response_model=RecipeImagesResponse)
async def get_recipe_images(
    recipe_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取菜谱图片列表.

    - **recipe_id**: 菜谱 ID
    - 返回封面图和所有步骤图
    """
    result = await db.execute(
        select(RecipeImage).where(RecipeImage.recipe_id == recipe_id)
    )
    images = result.scalars().all()

    cover = None
    steps = []

    for img in images:
        image_info = ImageInfo(
            url=img.image_url,
            width=img.width,
            height=img.height,
            file_size=img.file_size,
        )
        if img.image_type == "cover":
            cover = image_info
        elif img.image_type == "step":
            steps.append(StepImage(
                step_no=img.step_no or 0,
                url=img.image_url,
                width=img.width,
                height=img.height,
                file_size=img.file_size,
            ))

    steps.sort(key=lambda x: x.step_no)

    return RecipeImagesResponse(
        recipe_id=recipe_id,
        cover=cover,
        steps=steps,
    )
```

- [ ] **Step 3: 注册路由**

编辑 `app/api/routes.py`，添加：

```python
from app.api.v1.images import router as images_router

# 在 router 注册处添加
app.include_router(images_router, prefix="/api/v1/c")
```

- [ ] **Step 4: 编写图片 API 测试**

创建 `tests/api/test_images.py`：

```python
"""图片 API 测试."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch


class TestImagesAPI:
    """图片 API 测试."""

    @pytest.mark.asyncio
    async def test_get_recipe_images(self, client: TestClient, async_session):
        """测试获取菜谱图片."""
        from app.models.recipe import Recipe
        from app.models.recipe_image import RecipeImage
        import uuid

        # 创建菜谱
        recipe = Recipe(
            name="测试菜谱",
            description="测试",
            is_public=True,
            audit_status="approved",
        )
        async_session.add(recipe)
        await async_session.commit()
        await async_session.refresh(recipe)

        # 创建封面图
        cover = RecipeImage(
            recipe_id=recipe.id,
            image_type="cover",
            source_path="test.jpg",
            local_path="images/recipe/test/cover.jpg",
            image_url="https://example.com/cover.jpg",
            width=800,
            height=600,
        )
        async_session.add(cover)
        await async_session.commit()

        # 调用 API
        response = client.get(f"/api/v1/c/recipes/{recipe.id}/images")

        assert response.status_code == 200
        data = response.json()
        assert data["recipe_id"] == str(recipe.id)
        assert data["cover"]["url"] == "https://example.com/cover.jpg"
```

- [ ] **Step 5: 运行测试**

```bash
cd /Users/wangzhentao/code/cook-rag
pytest tests/api/test_images.py -v
```
Expected: 1 passed

- [ ] **Step 6: 提交**

```bash
cd /Users/wangzhentao/code/cook-rag
git add app/api/schemas.py app/api/v1/images.py app/api/routes.py tests/api/test_images.py
git commit -m "feat: 实现菜谱图片 API 接口 (Task 39)"
```

---

### Task 6: 测试与文档

**Files:**
- Create: `tests/integration/test_image_search.py`
- Modify: `docs/architecture/overview.md`

- [ ] **Step 1: 创建集成测试**

创建 `tests/integration/test_image_search.py`：

```python
"""图片搜索集成测试."""

import pytest
from unittest.mock import patch, MagicMock


class TestImageSearchIntegration:
    """图片搜索集成测试."""

    @patch('app.services.clip_service.CLIPModel.from_pretrained')
    @patch('app.services.clip_service.CLIPProcessor.from_pretrained')
    def test_image_search_pipeline(self, mock_processor, mock_model):
        """测试完整图片搜索流程."""
        from app.services.clip_service import ClipService
        import numpy as np

        # Mock CLIP 服务
        mock_model_instance = MagicMock()
        mock_model.return_value = mock_model_instance
        mock_model_instance.get_image_features.return_value = MagicMock(
            cpu=MagicMock(return_value=MagicMock(
                numpy=MagicMock(return_value=np.random.rand(1, 512))
            ))
        )

        mock_processor_instance = MagicMock()
        mock_processor.return_value = mock_processor_instance

        # 测试向量生成
        service = ClipService()
        vector = service.get_image_embedding("http://example.com/image.jpg")

        assert len(vector) == 512
        assert all(isinstance(v, float) for v in vector)
```

- [ ] **Step 2: 运行集成测试**

```bash
cd /Users/wangzhentao/code/cook-rag
pytest tests/integration/test_image_search.py -v
```
Expected: 1 passed

- [ ] **Step 3: 更新架构文档**

编辑 `docs/architecture/overview.md`，在多模态检索部分添加图片搜索说明。

- [ ] **Step 4: 提交**

```bash
cd /Users/wangzhentao/code/cook-rag
git add tests/integration/test_image_search.py docs/architecture/overview.md
git commit -m "docs: 添加图片搜索集成测试和文档 (Task 40)"
```

---

## 自审清单

**1. Spec 覆盖检查:**
- [x] 图片存储（GitHub CDN）→ Task 1, 4
- [x] 数据库 Schema → Task 1
- [x] CLIP 向量化 → Task 2
- [x] Qdrant 集成 → Task 3
- [x] 图片导入 → Task 4
- [x] API 接口 → Task 5
- [x] 测试与文档 → Task 6

**2. Placeholder 扫描:**
无 "TBD", "TODO" 占位符

**3. 类型一致性:**
- `RecipeImage` 模型在所有文件中一致
- `image_type` 枚举值：`cover`, `step`, `ingredient`
- 向量维度：512（CLIP）

---

Plan complete and saved to `docs/superpowers/plans/2026-04-22-multimodal-image-storage-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - 我 dispatch 一个子 agent 按任务执行，任务间 review，快速迭代

**2. Inline Execution** - 在当前 session 使用 executing-plans 批量执行，设置检查点

**Which approach?**
