#!/usr/bin/env python3
"""同步菜谱数据到 Qdrant 和 Elasticsearch。

使用方法:
    # 同步所有数据
    python scripts/sync_qdrant.py --all

    # 仅同步 Qdrant
    python scripts/sync_qdrant.py --qdrant

    # 仅同步 Elasticsearch
    python scripts/sync_qdrant.py --es
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Dict
import numpy as np

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models.recipe import Recipe
from app.models.ingredient import RecipeIngredient
from app.models.step import RecipeStep
from sqlalchemy import select
from sqlalchemy.orm import selectinload


def get_clip_service():
    """获取 CLIP 服务实例。"""
    from app.services.clip_service import ClipService
    return ClipService()


async def sync_to_qdrant(batch_size: int = 50):
    """将菜谱数据同步到 Qdrant。"""
    import json
    import urllib.request

    print("=" * 60)
    print("同步数据到 Qdrant（使用 REST API）")
    print("=" * 60)

    collection_name = settings.QDRANT_COLLECTION
    qdrant_url = settings.QDRANT_URL
    clip_service = get_clip_service()

    stats = {
        "recipes_processed": 0,
        "vectors_uploaded": 0,
        "failed": 0
    }

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Recipe)
            .options(selectinload(Recipe.ingredients), selectinload(Recipe.steps))
            .where(Recipe.is_public == True)
        )
        recipes = result.scalars().all()

    print(f"找到 {len(recipes)} 个公开菜谱")

    from app.services.embedding_service import get_embedding_service
    embedding_service = get_embedding_service()

    for i in range(0, len(recipes), batch_size):
        batch_recipes = recipes[i:i + batch_size]
        points = []

        for idx, recipe in enumerate(batch_recipes):
            try:
                vectors = {}

                name_vec = embedding_service.encode(recipe.name)
                vectors["name_vec"] = name_vec

                desc_text = recipe.description or ", ".join([ing.name for ing in recipe.ingredients[:10]])
                desc_vec = embedding_service.encode(desc_text)
                vectors["desc_vec"] = desc_vec

                step_text = " ".join([step.description for step in recipe.steps[:5]])
                step_vec = embedding_service.encode(step_text)
                vectors["step_vec"] = step_vec

                tag_text = ", ".join(recipe.tags) if recipe.tags else recipe.cuisine or ""
                tag_vec = embedding_service.encode(tag_text) if tag_text else [0.0] * 1024
                vectors["tag_vec"] = tag_vec

                image_vec = clip_service.get_text_embedding(recipe.name).tolist()
                vectors["image_vec"] = image_vec

                payload = {
                    "recipe_id": str(recipe.id),
                    "name": recipe.name,
                    "cuisine": recipe.cuisine or "其他",
                    "difficulty": recipe.difficulty or "medium",
                    "is_public": recipe.is_public,
                    "audit_status": recipe.audit_status or "approved"
                }

                points.append({
                    "id": i + idx,
                    "vector": vectors,
                    "payload": payload
                })
                stats["vectors_uploaded"] += 1

            except Exception as e:
                print(f"处理菜谱 {recipe.name} 失败：{e}")
                stats["failed"] += 1

        # 使用 REST API 上传
        if points:
            try:
                data = json.dumps({"points": points}).encode("utf-8")
                req = urllib.request.Request(
                    f"{qdrant_url}/collections/{collection_name}/points",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="PUT"
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    if result.get("status") == "ok":
                        print(f"已上传 {i + len(points)}/{len(recipes)} 个菜谱")
                    else:
                        print(f"上传返回异常状态：{result}")
            except Exception as e:
                print(f"上传 batch 失败：{e}")

        stats["recipes_processed"] += len(batch_recipes)

    print(f"\nQdrant 同步完成!")
    print(f"  处理菜谱：{stats['recipes_processed']}")
    print(f"  上传向量：{stats['vectors_uploaded']}")
    print(f"  失败：{stats['failed']}")


async def sync_to_elasticsearch(batch_size: int = 50):
    """将菜谱数据同步到 Elasticsearch。"""
    from elasticsearch import AsyncElasticsearch

    print("=" * 60)
    print("同步数据到 Elasticsearch")
    print("=" * 60)

    es = AsyncElasticsearch([settings.ELASTICSEARCH_URL])

    stats = {
        "recipes_processed": 0,
        "indexed": 0,
        "failed": 0
    }

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Recipe)
            .options(selectinload(Recipe.ingredients), selectinload(Recipe.steps))
            .where(Recipe.is_public == True)
        )
        recipes = result.scalars().all()

    print(f"找到 {len(recipes)} 个公开菜谱")

    for i in range(0, len(recipes), batch_size):
        batch_recipes = recipes[i:i + batch_size]

        for recipe in batch_recipes:
            try:
                # 构建 ES 文档
                doc = {
                    "recipe_id": str(recipe.id),
                    "name": recipe.name,
                    "description": recipe.description or "",
                    "cuisine": recipe.cuisine or "其他",
                    "difficulty": recipe.difficulty or "medium",
                    "tags": recipe.tags or [],
                    "ingredients": [ing.name for ing in recipe.ingredients],
                    "steps": [step.description for step in recipe.steps],
                    "is_public": recipe.is_public,
                    "audit_status": recipe.audit_status or "approved"
                }

                # 索引文档
                await es.index(
                    index=settings.ES_INDEX_NAME,
                    id=str(recipe.id),
                    document=doc
                )
                stats["indexed"] += 1

            except Exception as e:
                print(f"索引菜谱 {recipe.name} 失败：{e}")
                stats["failed"] += 1

        stats["recipes_processed"] += len(batch_recipes)
        print(f"已处理 {stats['recipes_processed']}/{len(recipes)} 个菜谱")

    # 刷新索引
    await es.indices.refresh(index=settings.ES_INDEX_NAME)

    await es.close()

    print(f"\nElasticsearch 同步完成!")
    print(f"  处理菜谱：{stats['recipes_processed']}")
    print(f"  索引文档：{stats['indexed']}")
    print(f"  失败：{stats['failed']}")

    return stats


async def main():
    parser = argparse.ArgumentParser(description="同步数据到 Qdrant 和 ES")
    parser.add_argument("--all", action="store_true", help="同步所有数据")
    parser.add_argument("--qdrant", action="store_true", help="仅同步 Qdrant")
    parser.add_argument("--es", action="store_true", help="仅同步 ES")
    parser.add_argument("--batch-size", type=int, default=50, help="批处理大小")
    args = parser.parse_args()

    if not any([args.all, args.qdrant, args.es]):
        args.all = True  # 默认同步所有

    if args.all or args.qdrant:
        await sync_to_qdrant(batch_size=args.batch_size)
        print()

    if args.all or args.es:
        await sync_to_elasticsearch(batch_size=args.batch_size)

    print("\n" + "=" * 60)
    print("同步完成!")
    print("=" * 60)
    print("\n下一步:")
    print("1. 启动 API 服务：uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print("2. 测试搜索：curl http://localhost:8000/api/v1/search/text?q=川菜")


if __name__ == "__main__":
    asyncio.run(main())
