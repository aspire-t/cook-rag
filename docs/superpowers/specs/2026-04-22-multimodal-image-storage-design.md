# CookRAG 多模态图片存储设计方案

**版本**: v1.0  
**日期**: 2026-04-22  
**状态**: 设计评审  
**作者**: System Architect  

---

## 目录

1. [需求概述](#1-需求概述)
2. [图片存储方案](#2-图片存储方案)
3. [数据库 Schema 变更](#3-数据库-schema-变更)
4. [向量化方案](#4-向量化方案)
5. [数据导入流程](#5-数据导入流程)
6. [API 接口设计](#6-api-接口设计)
7. [实施计划](#7-实施计划)
8. [风险与应对](#8-风险与应对)

---

## 1. 需求概述

### 1.1 背景

当前 CookRAG 系统已完整存储 HowToCook 菜谱的文本数据（菜名、描述、食材、步骤），但缺少图片存储能力。

king-jingxiang/HowToCook 仓库包含约 327 张图片，包括：
- **成品图**：每道菜谱的完成品展示
- **步骤图**：部分菜谱的关键步骤展示

### 1.2 需求目标

| 目标 | 说明 | 优先级 |
|------|------|--------|
| 图片存储 | 存储菜谱封面图和步骤图 | P0 |
| 图片展示 | API 返回图片 URL 供前端展示 | P0 |
| 以图搜菜 | 用户上传图片搜索相似菜谱 | P1 |
| 图文联合检索 | 文字搜索时结合图片相似度排序 | P2 |

### 1.3 设计原则

| 原则 | 说明 |
|------|------|
| 成本优先 | MVP 阶段零存储成本，使用 GitHub CDN |
| 渐进式扩展 | 后续可平滑迁移到 MinIO/S3 |
| 数据可控 | 图片同步到自有仓库，不依赖第三方 |
| 向量化预留 | 预留 CLIP 向量能力，支持多模态检索 |

---

## 2. 图片存储方案

### 2.1 存储架构

**选择：自有 GitHub 仓库 + Raw CDN**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              图片存储架构                                    │
└─────────────────────────────────────────────────────────────────────────────┘

king-jingxiang/HowToCook          您的仓库 (aspire-t/cook-rag-images)
     │                                    │
     │  1. Fork/同步图片                   │  2. 导入时关联
     ▼                                    ▼
┌─────────────┐                      ┌─────────────┐
│ dishes/     │  ───────────────►    │ images/     │
│ ├── meat/   │      图片文件         │ ├── recipe/ │
│ ├── veg/    │                      │ │   ┌───┐   │
│ └── ...     │                      │ │   │1.jpg│  │
└─────────────┘                      │ │   └───┘   │
                                     │ └── step/   │
                                     │     └───┘   │
                                     └──────┬──────┘
                                            │
                                            │ 3. CDN 访问
                                            ▼
                              https://raw.githubusercontent.com/
                              aspire-t/cook-rag-images/master/
                              images/recipe/{recipe_id}/{image}
```

### 2.2 目录结构

```
cook-rag-images/
├── images/
│   ├── recipe/              # 菜谱图片
│   │   └── {recipe_id}/     # 按菜谱 ID 分组
│   │       ├── cover.jpg    # 封面图
│   │       ├── step_1.jpg   # 步骤 1 图
│   │       ├── step_2.jpg   # 步骤 2 图
│   │       └── ...
│   └── ingredient/          # 食材图（可选扩展）
│       └── {ingredient_id}/
└── README.md
```

### 2.3 GitHub CDN URL 规则

**基础 URL**:
```
https://raw.githubusercontent.com/aspire-t/cook-rag-images/master
```

**拼接规则**:
```python
BASE_CDN_URL = "https://raw.githubusercontent.com/aspire-t/cook-rag-images/master"

# 封面图
cover_url = f"{BASE_CDN_URL}/images/recipe/{recipe_id}/cover.jpg"

# 步骤图
step_url = f"{BASE_CDN_URL}/images/recipe/{recipe_id}/step_{step_no}.jpg"
```

### 2.4 图片同步策略

| 阶段 | 策略 | 说明 |
|------|------|------|
| MVP | 手动同步 | 导入脚本下载并上传到自有仓库 |
| Phase 2 | GitHub Actions | 监听 king-jingxiang 仓库更新，自动同步 |
| Phase 3 | MinIO 迁移 | 如有 CDN 加速需求，迁移到对象存储 |

---

## 3. 数据库 Schema 变更

### 3.1 新增字段

```sql
-- recipes 表新增封面图字段
ALTER TABLE recipes 
ADD COLUMN cover_image_url VARCHAR(500),
ADD COLUMN cover_image_path VARCHAR(200);

-- recipe_steps 表复用已有 image_url 字段，新增 path 字段
ALTER TABLE recipe_steps 
ADD COLUMN image_path VARCHAR(200);

COMMENT ON COLUMN recipes.cover_image_url IS '菜谱封面图 CDN URL';
COMMENT ON COLUMN recipes.cover_image_path IS '封面图在图片仓库的相对路径';
COMMENT ON COLUMN recipe_steps.image_path IS '步骤图片在图片仓库的相对路径';
```

### 3.2 新建图片元数据表

```sql
CREATE TABLE recipe_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    step_no INTEGER,  -- NULL=封面图，1+=步骤图序号
    image_type VARCHAR(20) NOT NULL DEFAULT 'cover',  -- cover/step/ingredient
    source_path TEXT NOT NULL,  -- king-jingxiang 仓库原始路径
    local_path VARCHAR(200) NOT NULL,  -- 自己仓库的相对路径
    image_url VARCHAR(500) NOT NULL,  -- 完整 CDN URL
    width INTEGER,  -- 图片宽度
    height INTEGER,  -- 图片高度
    file_size INTEGER,  -- 文件大小（字节）
    clip_vector_id VARCHAR(100),  -- CLIP 向量 ID（Qdrant）
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_recipe_images_recipe ON recipe_images(recipe_id);
CREATE INDEX idx_recipe_images_type ON recipe_images(image_type, step_no);
CREATE INDEX idx_recipe_images_clip ON recipe_images(clip_vector_id) WHERE clip_vector_id IS NOT NULL;

COMMENT ON TABLE recipe_images IS '菜谱图片元数据表';
COMMENT ON COLUMN recipe_images.step_no IS '步骤序号，NULL 表示封面图';
COMMENT ON COLUMN recipe_images.source_path IS '原始 GitHub 仓库路径';
COMMENT ON COLUMN recipe_images.local_path IS '自有图片仓库相对路径';
COMMENT ON COLUMN recipe_images.clip_vector_id IS 'CLIP 图片向量在 Qdrant 的 ID';
```

### 3.3 Qdrant Schema 变更

```python
# app/services/qdrant_schema.py

IMAGE_VECTOR_SIZE = 512  # CLIP ViT-B/16 输出维度

def get_collection_config() -> dict:
    return {
        "vectors": {
            # 原有文本向量（BGE-M3, 1024 维）
            "name_vec": VectorParams(size=1024, distance=Distance.COSINE),
            "desc_vec": VectorParams(size=1024, distance=Distance.COSINE),
            "step_vec": VectorParams(size=1024, distance=Distance.COSINE),
            "tag_vec": VectorParams(size=1024, distance=Distance.COSINE),
            
            # 新增图片向量（CLIP, 512 维）
            "image_vec": VectorParams(size=IMAGE_VECTOR_SIZE, distance=Distance.COSINE),
        },
        "quantization_config": BinaryQuantization(
            binary=BinaryQuantizationConfig(always_ram=True)
        ),
        "shard_number": 1,
        "replication_factor": 1,
    }

# Payload 新增字段
PAYLOAD_SCHEMA = {
    # ... 原有字段 ...
    "has_image": {"type": "boolean", "description": "是否有图片"},
    "image_type": {"type": "keyword", "description": "图片类型：cover/step"},
}
```

---

## 4. 向量化方案

### 4.1 模型选择

**推荐：Chinese-CLIP（阿里开源）**

| 模型 | 维度 | 速度 | 精度 | 推荐理由 |
|------|------|------|------|----------|
| chinese-clip-vit-base-patch16 | 512 | 快 | 高 | 中文优化，MVP 推荐 |
| chinese-clip-vit-large-patch14 | 768 | 中 | 高 | 精度优先场景 |

**模型来源**: OFA-Sys/chinese-clip-vit-base-patch16 (HuggingFace)

### 4.2 部署方式

```python
# app/services/clip_service.py

from transformers import CLIPProcessor, CLIPModel
import torch
from PIL import Image
import requests
from io import BytesIO

class ClipService:
    """CLIP 图片向量化服务"""
    
    MODEL_NAME = "OFA-Sys/chinese-clip-vit-base-patch16"
    VECTOR_SIZE = 512
    
    def __init__(self):
        self.device = self._get_device()
        self.model = CLIPModel.from_pretrained(self.MODEL_NAME).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(self.MODEL_NAME)
        self.model.eval()
    
    def _get_device(self) -> str:
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    
    @torch.no_grad()
    def get_image_embedding(self, image_url: str) -> list:
        """
        生成图片向量
        
        Args:
            image_url: 图片 URL 或本地路径
            
        Returns:
            512 维归一化向量列表
        """
        # 加载图片
        if image_url.startswith("http"):
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content))
        else:
            image = Image.open(image_url)
        
        # 处理并生成向量
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        image_features = self.model.get_image_features(**inputs)
        
        # 归一化（COSINE 距离需要）
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        return image_features.cpu().numpy()[0].tolist()
    
    @torch.no_grad()
    def get_text_embedding(self, text: str) -> list:
        """
        生成文本向量（用于跨模态检索）
        
        Args:
            text: 中文文本
            
        Returns:
            512 维归一化向量列表
        """
        inputs = self.processor(text=text, return_tensors="pt").to(self.device)
        text_features = self.model.get_text_features(**inputs)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        return text_features.cpu().numpy()[0].tolist()


# 单例
_clip_service: Optional[ClipService] = None

def get_clip_service() -> ClipService:
    global _clip_service
    if _clip_service is None:
        _clip_service = ClipService()
    return _clip_service
```

### 4.3 跨模态检索能力

| 检索类型 | 说明 | 实现方式 |
|----------|------|----------|
| 文搜图 | 用户输入文字，返回相似图片 | text_vec → image_vec 相似度 |
| 图搜图 | 用户上传/选择图片，返回相似图片 | image_vec → image_vec 相似度 |
| 图文联合 | 文字 + 图片联合检索 | text_vec + image_vec 加权融合 |

---

## 5. 数据导入流程

### 5.1 整体流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         图片导入流程                                         │
└─────────────────────────────────────────────────────────────────────────────┘

1. 扫描 king-jingxiang 仓库
   │
   ▼
2. 解析 Markdown 提取图片引用
   │
   ▼
3. 下载图片到本地临时目录
   │
   ▼
4. (可选) 图片优化：压缩/转 WebP
   │
   ▼
5. 上传到自己 GitHub 仓库
   │
   ▼
6. 生成 CDN URL
   │
   ▼
7. 写入数据库 (recipe_images 表)
   │
   ▼
8. 调用 CLIP 生成图片向量
   │
   ▼
9. 写入 Qdrant (image_vec 字段)
```

### 5.2 图片解析规则

**Markdown 图片语法**:
```markdown
![描述](./图片名.jpg)
![描述](图片名.png)
```

**解析逻辑**:
```python
# app/services/image_importer.py

import re
import requests
from pathlib import Path
from typing import List, Tuple
from github import Github, InputGitTreeElement

IMAGE_REPO = "aspire-t/cook-rag-images"
GITHUB_TOKEN = "github_pat_xxx"
BASE_CDN_URL = "https://raw.githubusercontent.com/aspire-t/cook-rag-images/master"

class ImageImporter:
    """图片导入器"""
    
    def __init__(self):
        self.github = Github(GITHUB_TOKEN)
        self.image_repo = self.github.get_repo(IMAGE_REPO)
    
    def extract_images_from_markdown(self, md_path: Path, md_content: str) -> List[dict]:
        """
        从 Markdown 提取图片引用
        
        Returns:
            [{"source_path": "...", "image_type": "cover/step", "step_no": 1}]
        """
        images = []
        # 匹配 ![描述](./路径) 或 ![描述](路径)
        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        for match in re.finditer(pattern, md_content):
            desc, rel_path = match.groups()
            source_path = str(md_path.parent / rel_path)
            
            # 判断图片类型
            # 封面图：通常在文件顶部，描述包含菜名
            # 步骤图：描述包含"步骤"或文件名包含数字
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
    
    def download_and_upload_image(self, source_path: str, dest_path: str) -> str:
        """
        下载源图片并上传到自己仓库
        
        Returns:
            CDN URL
        """
        # 1. 从 king-jingxiang 下载
        source_url = f"https://raw.githubusercontent.com/king-jingxiang/HowToCook/master/{source_path}"
        response = requests.get(source_url)
        response.raise_for_status()
        image_data = response.content
        
        # 2. 上传到 GitHub
        self.image_repo.create_file(
            path=dest_path,
            message=f"Add image: {dest_path}",
            content=image_data,
            branch="master",
        )
        
        # 3. 返回 CDN URL
        return f"{BASE_CDN_URL}/{dest_path}"
    
    def import_recipe_images(self, recipe_id: str, recipe_name: str, md_path: Path) -> List[dict]:
        """
        导入单个菜谱的图片
        
        Returns:
            导入的图片元数据列表
        """
        md_content = md_path.read_text(encoding="utf-8")
        images = self.extract_images_from_markdown(md_path, md_content)
        
        imported = []
        for i, img in enumerate(images):
            # 生成目标路径
            if img["image_type"] == "cover":
                dest_path = f"images/recipe/{recipe_id}/cover.jpg"
            else:
                dest_path = f"images/recipe/{recipe_id}/step_{img['step_no'] or i}.jpg"
            
            try:
                cdn_url = self.download_and_upload_image(img["source_path"], dest_path)
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

### 5.3 批量导入脚本

```python
# scripts/import_images.py

#!/usr/bin/env python3
"""
从 HowToCook 仓库导入图片到自有仓库和数据库
"""

import asyncio
import aiohttp
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
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
        # 遍历所有菜谱 Markdown
        md_files = list(HOWTOCOOK_PATH.glob("dishes/**/*.md"))
        for md_file in md_files:
            # 查询数据库获取 recipe_id
            result = await conn.execute(
                "SELECT id FROM recipes WHERE name = :name",
                {"name": md_file.stem}
            )
            row = result.fetchone()
            if not row:
                continue
            
            recipe_id = row[0]
            
            # 导入图片
            images = importer.import_recipe_images(recipe_id, md_file.stem, md_file)
            
            for img in images:
                total_images += 1
                try:
                    # 写入数据库
                    await conn.execute("""
                        INSERT INTO recipe_images 
                        (recipe_id, image_type, step_no, source_path, local_path, image_url)
                        VALUES (:recipe_id, :image_type, :step_no, :source_path, :local_path, :image_url)
                    """, img)
                    
                    # 生成 CLIP 向量并写入 Qdrant
                    vector = clip_service.get_image_embedding(img["image_url"])
                    # ... Qdrant 上传逻辑
                    
                    success += 1
                    print(f"导入成功：{img['local_path']}")
                except Exception as e:
                    failed += 1
                    print(f"导入失败 {img['local_path']}: {e}")
    
    print(f"\n=== 导入完成 ===")
    print(f"总计：{total_images} 张图片")
    print(f"成功：{success} 张")
    print(f"失败：{failed} 张")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 6. API 接口设计

### 6.1 图片列表 API

```http
GET /api/v1/c/recipes/{recipe_id}/images
Authorization: Bearer {token}

# Response 200
{
    "code": 0,
    "message": "success",
    "data": {
        "recipe_id": "uuid",
        "cover": {
            "url": "https://raw.githubusercontent.com/...",
            "width": 800,
            "height": 600,
            "file_size": 102400
        },
        "steps": [
            {
                "step_no": 1,
                "url": "https://raw.githubusercontent.com/...",
                "width": 800,
                "height": 600,
                "file_size": 81920
            },
            {
                "step_no": 2,
                "url": "...",
                "width": 800,
                "height": 600
            }
        ]
    },
    "meta": {
        "request_id": "req_img_001",
        "timestamp": 1713801600,
        "latency_ms": 25
    }
}
```

### 6.2 以图搜菜 API

```http
POST /api/v1/c/search/image
Content-Type: application/json
Authorization: Bearer {token}

# Request
{
    "image_url": "https://example.com/photo.jpg",  # 或 base64
    "limit": 10,
    "search_mode": "visual"  # visual: 纯图片搜索，multimodal: 图文联合
}

# Response 200
{
    "code": 0,
    "message": "success",
    "data": {
        "search_type": "visual_similarity",
        "query_vector_type": "image_vec",
        "recipes": [
            {
                "id": "uuid",
                "name": "宫保鸡丁",
                "cuisine": "川菜",
                "image_url": "https://...",
                "similarity_score": 0.92,
                "match_reasons": ["图片视觉相似"]
            },
            ...
        ]
    }
}
```

### 6.3 Schema 定义

```python
# app/api/schemas.py

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from enum import Enum

class ImageType(str, Enum):
    COVER = "cover"
    STEP = "step"
    INGREDIENT = "ingredient"

class ImageInfo(BaseModel):
    """图片信息"""
    url: str = Field(..., description="图片 CDN URL")
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")

class StepImage(ImageInfo):
    """步骤图片"""
    step_no: int = Field(..., description="步骤序号")

class RecipeImagesResponse(BaseModel):
    """菜谱图片列表响应"""
    recipe_id: str
    cover: Optional[ImageInfo] = None
    steps: List[StepImage] = []

class ImageSearchMode(str, Enum):
    VISUAL = "visual"  # 纯图片搜索
    MULTIMODAL = "multimodal"  # 图文联合

class ImageSearchRequest(BaseModel):
    """以图搜菜请求"""
    image_url: str = Field(..., description="图片 URL 或 base64")
    limit: int = Field(10, ge=1, le=50, description="返回数量")
    search_mode: ImageSearchMode = Field(ImageSearchMode.VISUAL, description="搜索模式")

class ImageSearchResult(BaseModel):
    """以图搜菜结果项"""
    id: str
    name: str
    cuisine: str
    image_url: str
    similarity_score: float = Field(..., description="相似度分数")
    match_reasons: List[str]
```

---

## 7. 实施计划

### 7.1 任务分解

| 阶段 | 任务 | 说明 | 预估工时 |
|------|------|------|----------|
| **Phase 1** | 创建图片仓库 | Fork 或新建 cook-rag-images | 0.5h |
| **Phase 2** | 数据库迁移 | 添加字段和 recipe_images 表 | 1h |
| **Phase 3** | 图片导入脚本 | 扫描→下载→上传→写库 | 3h |
| **Phase 4** | CLIP 服务集成 | 部署模型 + 批量生成向量 | 2h |
| **Phase 5** | Qdrant 集成 | 新增 image_vec 字段 + 检索 | 2h |
| **Phase 6** | API 开发 | 图片列表、以图搜菜 | 2h |
| **Phase 7** | 测试与文档 | 单元测试、API 文档 | 1.5h |

**总工时**: 约 12 小时

### 7.2 任务依赖

```
Phase 1 ─┬─► Phase 2 ─► Phase 3 ─┬─► Phase 4 ─► Phase 5 ─► Phase 6 ─► Phase 7
         │                        │
         └────────────────────────┘
              (图片上传后才能向量化)
```

---

## 8. 风险与应对

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|----------|
| GitHub CDN 国内访问慢 | 用户体验差 | 中 | 后续迁移到国内 CDN 或 MinIO |
| CLIP 模型推理慢 | 以图搜菜延迟高 | 中 | 批量预处理 + 向量缓存 |
| 图片版权问题 | 法律风险 | 低 | HowToCook 为 MIT 许可，图片可商用 |
| 图片仓库同步不及时 | 图片缺失 | 中 | GitHub Actions 自动同步 |

---

## 附录

### A. 配置变更

```python
# app/core/config.py

class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # 图片仓库配置
    IMAGE_REPO_NAME: str = "aspire-t/cook-rag-images"
    IMAGE_REPO_TOKEN: str = ""  # GitHub PAT
    IMAGE_BASE_CDN_URL: str = "https://raw.githubusercontent.com/aspire-t/cook-rag-images/master"
    
    # CLIP 模型配置
    CLIP_MODEL_NAME: str = "OFA-Sys/chinese-clip-vit-base-patch16"
    CLIP_DEVICE: str = "auto"  # auto/cuda/mps/cpu
    
    class Config:
        env_file = ".env"
```

### B. 环境变量

```bash
# .env

# 图片仓库
IMAGE_REPO_NAME=aspire-t/cook-rag-images
IMAGE_REPO_TOKEN=github_pat_xxx
IMAGE_BASE_CDN_URL=https://raw.githubusercontent.com/aspire-t/cook-rag-images/master

# CLIP 模型
CLIP_MODEL_NAME=OFA-Sys/chinese-clip-vit-base-patch16
CLIP_DEVICE=auto
```

---

**文档结束**

请审阅以上设计文档。如有修改意见请提出，确认后将进入 implementation plan 阶段。
