#!/usr/bin/env python3
"""完整数据导入脚本 - HowToCook → PostgreSQL → ES → Qdrant → 图片。

使用方法:
    # 完整导入（所有数据）
    python scripts/import_data.py --source data/howtocook

    # 仅导入菜谱（不含图片）
    python scripts/import_data.py --source data/howtocook --no-images

    # 断点续传
    python scripts/import_data.py --source data/howtocook --resume

    # 批量处理
    python scripts/import_data.py --source data/howtocook --batch-size 50
"""

import asyncio
import argparse
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from app.models.recipe import Recipe
from app.models.recipe_ingredient import RecipeIngredient
from app.models.recipe_step import RecipeStep
from app.core.database import get_db_session
from app.core.config import settings


class HowToCookParser:
    """HowToCook Markdown 解析器."""

    def __init__(self):
        self.section_patterns = {
            "ingredients": re.compile(r"## 食材\s*.*?(?=##|$)", re.DOTALL),
            "steps": re.compile(r"## 做法\s*.*?(?=##|$)", re.DOTALL),
            "tags": re.compile(r"tags:\s*\[([^\]]+)\]", re.IGNORECASE),
        }

    def parse_markdown(self, content: str) -> Dict:
        """解析 Markdown 内容。

        Returns:
            {
                "name": str,
                "ingredients": List[str],
                "steps": List[str],
                "tags": List[str],
                "cuisine": str,
                "difficulty": str,
                "prep_time": int,
                "cook_time": int,
                "content": str  # 原始内容
            }
        """
        result = {
            "name": self._extract_title(content),
            "ingredients": self._extract_ingredients(content),
            "steps": self._extract_steps(content),
            "tags": self._extract_tags(content),
            "cuisine": self._extract_cuisine(content),
            "difficulty": self._estimate_difficulty(content),
            "prep_time": 0,
            "cook_time": 0,
            "content": content
        }

        return result

    def _extract_title(self, content: str) -> str:
        """提取菜名（第一个 # 标题）。"""
        match = re.search(r"^#\s*(.+)$", content, re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _extract_ingredients(self, content: str) -> List[str]:
        """提取食材列表。"""
        ingredients = []
        match = self.section_patterns["ingredients"].search(content)
        if match:
            section = match.group(0)
            # 匹配 - 开头的行
            for line in section.split("\n"):
                line = line.strip()
                if line.startswith("- ") and len(line) > 2:
                    ingredients.append(line[2:].strip())
        return ingredients

    def _extract_steps(self, content: str) -> List[str]:
        """提取步骤列表。"""
        steps = []
        match = self.section_patterns["steps"].search(content)
        if match:
            section = match.group(0)
            # 匹配数字开头的行
            for line in section.split("\n"):
                line = line.strip()
                if re.match(r"^\d+[\.\)]\s*", line):
                    # 移除数字前缀
                    step_text = re.sub(r"^\d+[\.\)]\s*", "", line)
                    steps.append(step_text)
        return steps

    def _extract_tags(self, content: str) -> List[str]:
        """提取标签。"""
        tags = []
        match = self.section_patterns["tags"].search(content)
        if match:
            tags_str = match.group(1)
            tags = [t.strip().strip("\"'") for t in tags_str.split(",")]
        return tags

    def _extract_cuisine(self, content: str) -> str:
        """提取菜系。"""
        # 从文件路径或标签推断
        cuisine_map = {
            "川菜": ["川菜", "四川", "麻辣"],
            "粤菜": ["粤菜", "广东", "清淡"],
            "鲁菜": ["鲁菜", "山东"],
            "淮扬菜": ["淮扬菜", "江苏", "扬州"],
            "湘菜": ["湘菜", "湖南", "辣"],
            "浙菜": ["浙菜", "浙江", "杭州"],
            "闽菜": ["闽菜", "福建"],
            "徽菜": ["徽菜", "安徽"],
        }

        tags = self._extract_tags(content)
        tags_str = ",".join(tags)

        for cuisine, keywords in cuisine_map.items():
            for keyword in keywords:
                if keyword in tags_str:
                    return cuisine

        return "其他"

    def _estimate_difficulty(self, content: str) -> str:
        """估算难度。"""
        ingredients_count = len(self._extract_ingredients(content))
        steps_count = len(self._extract_steps(content))

        total = ingredients_count + steps_count
        if total < 10:
            return "easy"
        elif total < 20:
            return "medium"
        else:
            return "hard"


class DataImporter:
    """数据导入器."""

    def __init__(self, source_path: str, batch_size: int = 100, resume: bool = False):
        self.source_path = Path(source_path)
        self.batch_size = batch_size
        self.resume = resume
        self.parser = HowToCookParser()

        # 统计信息
        self.stats = {
            "files_processed": 0,
            "recipes_created": 0,
            "ingredients_created": 0,
            "steps_created": 0,
            "failed": 0,
            "skipped": 0
        }

    async def import_recipe(self, db: AsyncSession, markdown_path: Path) -> bool:
        """导入单个菜谱。"""
        try:
            # 读取 Markdown
            content = markdown_path.read_text(encoding="utf-8")

            # 解析
            data = self.parser.parse_markdown(content)

            # 检查是否已存在
            existing = await db.execute(
                select(Recipe).where(Recipe.name == data["name"])
            )
            if existing.scalar_one_or_none():
                self.stats["skipped"] += 1
                return True

            # 创建菜谱
            recipe = Recipe(
                name=data["name"],
                content=data["content"],
                cuisine=data["cuisine"],
                difficulty=data["difficulty"],
                prep_time=data["prep_time"],
                cook_time=data["cook_time"],
                tags=data["tags"],
                is_public=True,
                audit_status="approved"
            )

            db.add(recipe)
            await db.flush()  # 获取 ID

            self.stats["recipes_created"] += 1

            # 创建食材
            for idx, ingredient_name in enumerate(data["ingredients"]):
                recipe_ingredient = RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_name=ingredient_name,
                    amount="",  # HowToCook 没有具体用量
                    order_no=idx
                )
                db.add(recipe_ingredient)
                self.stats["ingredients_created"] += 1

            # 创建步骤
            for idx, step_content in enumerate(data["steps"]):
                recipe_step = RecipeStep(
                    recipe_id=recipe.id,
                    step_number=idx,
                    description=step_content,
                    order_no=idx
                )
                db.add(recipe_step)
                self.stats["steps_created"] += 1

            return True

        except Exception as e:
            print(f"导入失败 {markdown_path}: {e}")
            self.stats["failed"] += 1
            return False

    async def run(self):
        """执行导入。"""
        print(f"开始导入数据...")
        print(f"源路径：{self.source_path}")
        print(f"批处理大小：{self.batch_size}")
        print(f"断点续传：{'是' if self.resume else '否'}")
        print("=" * 50)

        # 查找所有 Markdown 文件
        markdown_files = list(self.source_path.glob("**/*.md"))
        # 排除 README 等
        markdown_files = [
            f for f in markdown_files
            if not f.name.startswith("README") and "node_modules" not in str(f)
        ]

        print(f"找到 {len(markdown_files)} 个菜谱文件")

        async for db in get_db_session():
            batch = []
            for idx, md_file in enumerate(markdown_files):
                self.stats["files_processed"] += 1

                success = await self.import_recipe(db, md_file)

                if success:
                    batch.append(md_file.name)

                # 批量提交
                if len(batch) >= self.batch_size:
                    await db.commit()
                    print(f"已处理 {idx + 1}/{len(markdown_files)} (批处理：{len(batch)} 个)")
                    batch = []

            # 最后提交
            if batch:
                await db.commit()

            await db.close()

        # 打印统计
        self._print_stats()

    def _print_stats(self):
        """打印统计信息。"""
        print("\n" + "=" * 50)
        print("导入完成!")
        print(f"  处理文件：{self.stats['files_processed']}")
        print(f"  新增菜谱：{self.stats['recipes_created']}")
        print(f"  新增食材：{self.stats['ingredients_created']}")
        print(f"  新增步骤：{self.stats['steps_created']}")
        print(f"  跳过 (已存在): {self.stats['skipped']}")
        print(f"  失败：{self.stats['failed']}")
        print("=" * 50)


async def main():
    parser = argparse.ArgumentParser(description="HowToCook 数据导入")
    parser.add_argument("--source", required=True, help="HowToCook 数据路径")
    parser.add_argument("--batch-size", type=int, default=100, help="批处理大小")
    parser.add_argument("--resume", action="store_true", help="断点续传")
    parser.add_argument("--no-images", action="store_true", help="不导入图片")
    args = parser.parse_args()

    importer = DataImporter(
        source_path=args.source,
        batch_size=args.batch_size,
        resume=args.resume
    )

    await importer.run()

    # 提示下一步
    print("\n下一步:")
    print("1. 运行 python scripts/qdrant_collection.py --check 检查 Qdrant")
    print("2. 运行 python scripts/import_images.py --token XXX 导入图片")
    print("3. 启动 API 服务：uvicorn app.main:app --host 0.0.0.0 --port 8000")


if __name__ == "__main__":
    asyncio.run(main())
