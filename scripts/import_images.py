#!/usr/bin/env python3
"""图片导入脚本 - 从 HowToCook Markdown 导入所有图片。

使用方法:
    python scripts/import_images.py --token YOUR_GITHUB_TOKEN

依赖:
    - GitHub Token (需要 repo 权限)
    - 已配置 IMAGE_REPO_OWNER 和 IMAGE_REPO_NAME
"""

import asyncio
import aiohttp
import base64
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import re
from PIL import Image
import io

# 添加项目路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.clip_service import get_clip_service
from app.core.database import AsyncSessionLocal
from app.models.recipe_image import RecipeImage
from app.models.recipe import Recipe
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class ImageImporter:
    """图片导入器."""

    def __init__(self, token: str):
        self.token = token
        self.owner = settings.IMAGE_REPO_OWNER
        self.repo = settings.IMAGE_REPO_NAME
        self.base_cdn_url = settings.IMAGE_BASE_CDN_URL
        self.clip_service = get_clip_service()
        self.uploaded_count = 0
        self.failed_count = 0

    async def upload_to_github(
        self,
        path: str,
        content: bytes,
        message: str = "Upload image"
    ) -> dict:
        """上传图片到 GitHub 仓库。"""
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/{path}"

        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        async with aiohttp.ClientSession() as session:
            # 检查文件是否已存在
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    sha = data.get("sha")
                else:
                    sha = None

            # 上传文件
            content_b64 = base64.b64encode(content).decode("utf-8")
            payload = {
                "message": message,
                "content": content_b64
            }
            if sha:
                payload["sha"] = sha

            async with session.put(url, json=payload, headers=headers) as resp:
                result = await resp.json()
                if resp.status not in [200, 201]:
                    raise Exception(f"Upload failed: {result}")
                return result

    def parse_markdown_images(self, markdown: str) -> List[Dict]:
        """解析 Markdown 中的图片。

        返回：[{"url": xxx, "alt": xxx, "type": "cover/step"}]
        """
        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = re.findall(pattern, markdown)

        images = []
        for alt, url in matches:
            image_type = "step"
            if "封面" in alt or "成品" in alt or "cover" in alt.lower():
                image_type = "cover"
            elif "步骤" in alt or re.search(r'步骤？\d+', alt):
                image_type = "step"

            images.append({
                "alt": alt,
                "url": url,
                "type": image_type
            })

        return images

    def get_image_metadata(self, content: bytes) -> Dict:
        """获取图片元数据。"""
        img = Image.open(io.BytesIO(content))
        return {
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "size": len(content)
        }

    def convert_to_raw_url(self, url: str) -> str:
        """转换 GitHub blob URL 为 raw URL。"""
        if "github.com" in url and "/blob/" in url:
            return url.replace("/blob/", "/raw/")
        return url

    async def download_image(self, session: aiohttp.ClientSession, url: str) -> Optional[bytes]:
        """下载图片。"""
        raw_url = self.convert_to_raw_url(url)
        try:
            async with session.get(raw_url) as resp:
                if resp.status == 200:
                    return await resp.read()
        except Exception as e:
            print(f"  下载失败 {url}: {e}")
        return None

    async def import_recipe_images(
        self,
        db: AsyncSession,
        recipe: Recipe,
        session: aiohttp.ClientSession
    ) -> int:
        """导入单个菜谱的图片。"""
        if not recipe.content:
            return 0

        images = self.parse_markdown_images(recipe.content)
        if not images:
            return 0

        created_count = 0
        for idx, img_info in enumerate(images):
            try:
                # 下载图片
                content = await self.download_image(session, img_info["url"])
                if not content:
                    self.failed_count += 1
                    continue

                # 获取元数据
                metadata = self.get_image_metadata(content)

                # 生成路径
                step_no = idx if img_info["type"] == "step" else None
                ext = metadata.get("format", "jpg").lower()
                local_path = f"recipes/{recipe.id}/{img_info['type']}_{idx}.{ext}"

                # 上传到 GitHub
                await self.upload_to_github(
                    path=local_path,
                    content=content,
                    message=f"Upload {img_info['type']} image for recipe {recipe.id}"
                )
                self.uploaded_count += 1

                # CDN URL
                cdn_url = f"{self.base_cdn_url}{local_path}"

                # CLIP 向量
                img = Image.open(io.BytesIO(content)).convert("RGB")
                vector = self.clip_service.get_image_embedding(img)

                # 创建记录
                recipe_image = RecipeImage(
                    recipe_id=recipe.id,
                    step_no=step_no,
                    image_type=img_info["type"],
                    source_path=img_info["url"],
                    local_path=local_path,
                    image_url=cdn_url,
                    width=metadata["width"],
                    height=metadata["height"],
                    file_size=metadata["size"],
                    clip_vector_id=f"recipe_{recipe.id}_{img_info['type']}_{idx}"
                )

                db.add(recipe_image)
                created_count += 1

            except Exception as e:
                print(f"  处理图片失败 {img_info['url']}: {e}")
                self.failed_count += 1

        return created_count

    async def run(self, dry_run: bool = False) -> Dict:
        """执行导入。"""
        print(f"开始导入图片...")
        print(f"目标仓库：{self.owner}/{self.repo}")
        print(f"CDN 基础 URL: {self.base_cdn_url}")

        stats = {
            "recipes_processed": 0,
            "images_uploaded": 0,
            "images_failed": 0,
            "db_records": 0
        }

        async with aiohttp.ClientSession() as http_session:
            async with AsyncSessionLocal() as db:
                # 获取所有菜谱
                result = await db.execute(select(Recipe))
                recipes = result.scalars().all()

                print(f"找到 {len(recipes)} 个菜谱")

                for idx, recipe in enumerate(recipes):
                    if idx % 50 == 0:
                        print(f"处理进度：{idx}/{len(recipes)}")

                    try:
                        count = await self.import_recipe_images(db, recipe, http_session)
                        if count > 0:
                            stats["db_records"] += count
                            # 每 10 个菜谱提交一次
                            if idx % 10 == 0:
                                await db.commit()
                    except Exception as e:
                        print(f"处理菜谱 {recipe.id} 失败：{e}")

                    stats["recipes_processed"] += 1

                # 最后提交
                await db.commit()

        stats["images_uploaded"] = self.uploaded_count
        stats["images_failed"] = self.failed_count

        return stats


async def main():
    parser = argparse.ArgumentParser(description="导入 HowToCook 图片")
    parser.add_argument("--token", required=True, help="GitHub Token")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不实际上传")
    args = parser.parse_args()

    importer = ImageImporter(token=args.token)
    stats = await importer.run(dry_run=args.dry_run)

    print("\n" + "=" * 50)
    print("导入完成!")
    print(f"  处理菜谱数：{stats['recipes_processed']}")
    print(f"  上传图片数：{stats['images_uploaded']}")
    print(f"  失败图片数：{stats['images_failed']}")
    print(f"  数据库记录：{stats['db_records']}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
