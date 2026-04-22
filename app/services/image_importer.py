"""图片导入服务 - 从 HowToCook Markdown 导入图片."""

import aiohttp
import base64
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re
from PIL import Image
import io

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

    async def upload_to_github(
        self,
        path: str,
        content: bytes,
        message: str = "Upload image"
    ) -> dict:
        """上传图片到 GitHub 仓库。

        Args:
            path: 存储路径（相对路径）
            content: 图片二进制内容
            message: commit message

        Returns:
            上传结果
        """
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/{path}"

        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # 检查文件是否已存在
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    # 文件已存在，获取 sha
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

        Args:
            markdown: Markdown 内容

        Returns:
            图片列表：[{"url": xxx, "alt": xxx, "type": "cover/step"}]
        """
        # 匹配 Markdown 图片语法：![alt](url)
        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = re.findall(pattern, markdown)

        images = []
        for alt, url in matches:
            # 判断图片类型
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
        """获取图片元数据。

        Args:
            content: 图片二进制内容

        Returns:
            {"width": x, "height": y, "format": z, "size": z}
        """
        img = Image.open(io.BytesIO(content))
        return {
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "size": len(content)
        }

    async def import_recipe_images(
        self,
        recipe_id: int,
        markdown_content: str,
        source_repo: str = "king-jingxiang/HowToCook"
    ) -> List[RecipeImage]:
        """导入菜谱图片。

        Args:
            recipe_id: 菜谱 ID
            markdown_content: Markdown 内容
            source_repo: 源仓库

        Returns:
            创建的 RecipeImage 列表
        """
        images = self.parse_markdown_images(markdown_content)
        created_images = []

        async with AsyncSessionLocal() as db:
            for idx, img_info in enumerate(images):
                # 下载图片
                img_url = img_info["url"]
                # 转换为 raw 地址
                if "github.com" in img_url and "/blob/" in img_url:
                    img_url = img_url.replace("/blob/", "/raw/")

                async with aiohttp.ClientSession() as session:
                    async with session.get(img_url) as resp:
                        if resp.status != 200:
                            continue
                        content = await resp.read()

                # 获取元数据
                metadata = self.get_image_metadata(content)

                # 生成存储路径
                step_no = idx if img_info["type"] == "step" else None
                local_path = f"recipes/{recipe_id}/{img_info['type']}_{idx}.jpg"

                # 上传到 GitHub
                await self.upload_to_github(
                    path=local_path,
                    content=content,
                    message=f"Upload {img_info['type']} image for recipe {recipe_id}"
                )

                # 生成 CDN URL
                cdn_url = f"{self.base_cdn_url}{local_path}"

                # 获取 CLIP 向量
                img = Image.open(io.BytesIO(content)).convert("RGB")
                vector = self.clip_service.get_image_embedding(img)

                # 创建记录
                recipe_image = RecipeImage(
                    recipe_id=recipe_id,
                    step_no=step_no,
                    image_type=img_info["type"],
                    source_path=img_info["url"],
                    local_path=local_path,
                    image_url=cdn_url,
                    width=metadata["width"],
                    height=metadata["height"],
                    file_size=metadata["size"],
                    clip_vector_id=f"recipe_{recipe_id}_{img_info['type']}_{idx}"
                )

                db.add(recipe_image)
                created_images.append(recipe_image)

            await db.commit()

        return created_images
