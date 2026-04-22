#!/usr/bin/env python3
"""
从 HowToCook 仓库导入菜谱数据到 PostgreSQL 数据库.

用法:
    python3 scripts/import_howtocook.py
"""

import asyncio
import re
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from datetime import datetime, timezone

# ==================== 配置 ====================

HOWTOCOOK_PATH = Path("/tmp/HowToCook")
DATABASE_URL = "postgresql+asyncpg://cookrag:password@localhost:5432/cookrag"

# ==================== 解析器 ====================


def parse_difficulty(text: str) -> Optional[str]:
    """解析难度：★ -> easy/medium/hard"""
    if not text:
        return None
    star_count = text.count("★")
    if star_count <= 2:
        return "easy"
    elif star_count <= 4:
        return "medium"
    else:
        return "hard"


def parse_category(dir_path: str) -> Optional[str]:
    """根据目录路径映射菜系分类"""
    category_map = {
        "meat_dish": "荤菜",
        "vegetable_dish": "素菜",
        "aquatic": "水产",
        "breakfast": "早餐",
        "dessert": "甜点",
        "drink": "饮品",
        "soup": "汤羹",
        "staple": "主食",
        "condiment": "调料",
        "semi-finished": "半成品",
    }
    for key, value in category_map.items():
        if key in dir_path:
            return value
    return None


def parse_ingredients(section: str) -> List[dict]:
    """解析食材部分"""
    ingredients = []
    lines = section.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line or line.startswith("* ") or line.startswith("- "):
            line = line[2:] if line.startswith("* ") or line.startswith("- ") else line

            # 跳过非食材行
            if any(skip in line.lower() for skip in ["每次制作", "总量", "份数", "原材料"]):
                continue

            # 尝试解析食材：名称 + 用量
            # 格式："猪肉 300g" 或 "猪肉 300 g" 或 "猪肉 (300g)"
            match = re.match(r"^(.+?)(\d+(?:\.\d+)?)\s*(g|ml|kg|个|勺|根|片|瓣|只)?", line)
            if match:
                name = match.group(1).strip()
                try:
                    amount = float(match.group(2))
                except ValueError:
                    amount = None
                unit = match.group(3) if match.group(3) else None

                # 清理名称
                name = re.sub(r"[（(].*?[）)]", "", name).strip()
                name = name.rstrip(" ,;:;")

                if name and len(name) < 50:  # 过滤太长的行
                    ingredients.append({
                        "name": name,
                        "amount": amount,
                        "unit": unit,
                    })
            elif line and len(line) < 30:  # 短行可能是食材名
                # 去除可选标记
                line = line.replace("（可选）", "").replace("(可选)", "").strip()
                if line and not line.startswith("#"):
                    ingredients.append({
                        "name": line,
                        "amount": None,
                        "unit": None,
                    })

    return ingredients[:20]  # 限制最多 20 种食材


def parse_steps(section: str) -> List[dict]:
    """解析步骤部分"""
    steps = []
    lines = section.strip().split("\n")

    step_no = 1
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 跳过非步骤行
        if any(skip in line for skip in ["附加内容", "Issue", "Pull request", "参考资料", "示例菜"]):
            continue

        # 解析步骤：以 * 或 - 或数字开头
        if line.startswith("* ") or line.startswith("- "):
            line = line[2:]
        elif re.match(r"^\d+[\.,]", line):
            line = re.sub(r"^\d+[\.,]\s*", "", line)

        # 提取时间信息 (如 "5 S", "60 S", "3 分钟")
        duration = None
        time_match = re.search(r"(\d+)\s*(S|秒 | 分钟|min)", line, re.IGNORECASE)
        if time_match:
            seconds = int(time_match.group(1))
            unit = time_match.group(2).lower()
            if "分钟" in unit or "min" in unit:
                duration = seconds * 60
            else:
                duration = seconds

        if line and len(line) > 5:  # 过滤太短的行
            steps.append({
                "step_no": step_no,
                "description": line[:500],  # 限制长度
                "duration_seconds": duration,
            })
            step_no += 1

    return steps


def parse_markdown(file_path: Path) -> Optional[dict]:
    """解析 Markdown 菜谱文件"""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  读取失败 {file_path}: {e}")
        return None

    # 提取菜名（从文件名或标题）
    name_match = re.search(r"^#\s*(.+?)的做法", content)
    if name_match:
        name = name_match.group(1).strip()
    else:
        name = file_path.parent.name or file_path.stem

    # 提取描述（标题后的第一段）
    description = ""
    desc_match = re.search(r"的做法\s*\n+\n*(.+?)(?:\n\n|## )", content, re.DOTALL)
    if desc_match:
        description = desc_match.group(1).strip()[:500]

    # 提取难度
    difficulty_text = ""
    diff_match = re.search(r"预估烹饪难度：([★☆]+)", content)
    if diff_match:
        difficulty_text = diff_match.group(1)
    difficulty = parse_difficulty(difficulty_text)
    star_rating = difficulty_text if difficulty_text else None  # 保存原始星级

    # 提取菜系分类（从目录路径）
    rel_path = str(file_path.relative_to(HOWTOCOOK_PATH / "dishes"))
    cuisine = parse_category(rel_path)

    # 分割章节
    sections = re.split(r"^##\s+", content, flags=re.MULTILINE)

    ingredients = []
    steps = []
    prep_time = None
    cook_time = None

    for section in sections:
        if section.startswith("必备原料"):
            ingredients = parse_ingredients(section)
        elif section.startswith("操作"):
            steps = parse_steps(section)
        elif section.startswith("计算"):
            # 尝试从计算部分提取时间
            time_match = re.search(r"烹饪时间.*?(\d+)", section)
            if time_match:
                cook_time = int(time_match.group(1))
            prep_match = re.search(r"准备时间.*?(\d+)", section)
            if prep_match:
                prep_time = int(prep_match.group(1))

    # 如果没有解析到食材或步骤，跳过
    if not ingredients and not steps:
        return None

    # 生成标签
    tags = []
    if cuisine:
        tags.append(cuisine)
    if difficulty == "easy":
        tags.append("简单")
    elif difficulty == "medium":
        tags.append("中等")
    if cook_time and cook_time < 15:
        tags.append("快手菜")
    if "辣" in description or "麻辣" in description or "香辣" in description:
        tags.append("辣")

    return {
        "id": uuid.uuid4(),
        "name": name,
        "description": description or f"{name}的做法",
        "cuisine": cuisine,
        "difficulty": difficulty,
        "star_rating": star_rating,
        "prep_time": prep_time,
        "cook_time": cook_time,
        "servings": 1,
        "tags": tags,
        "source_url": f"https://github.com/Anduin2017/HowToCook/blob/master/{file_path.relative_to(HOWTOCOOK_PATH)}",
        "source_type": "howtocook",
        "is_public": True,
        "audit_status": "approved",
        "ingredients": ingredients,
        "steps": steps,
    }


# ==================== 数据库导入 ====================


async def import_recipe(session: AsyncSession, recipe_data: dict):
    """导入单个菜谱到数据库"""
    from app.models.recipe import Recipe
    from app.models.ingredient import RecipeIngredient
    from app.models.step import RecipeStep

    # 创建菜谱
    recipe = Recipe(
        id=recipe_data["id"],
        name=recipe_data["name"],
        description=recipe_data["description"],
        cuisine=recipe_data["cuisine"],
        difficulty=recipe_data["difficulty"],
        star_rating=recipe_data["star_rating"],
        prep_time=recipe_data["prep_time"],
        cook_time=recipe_data["cook_time"],
        servings=recipe_data["servings"],
        tags=recipe_data["tags"],
        source_url=recipe_data["source_url"],
        source_type=recipe_data["source_type"],
        is_public=recipe_data["is_public"],
        audit_status=recipe_data["audit_status"],
    )

    session.add(recipe)
    await session.flush()  # 获取生成的 ID

    # 创建食材
    for i, ing in enumerate(recipe_data["ingredients"]):
        ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            name=ing["name"],
            amount=ing["amount"],
            unit=ing["unit"],
            sequence=i,
        )
        session.add(ingredient)

    # 创建步骤
    for step in recipe_data["steps"]:
        recipe_step = RecipeStep(
            recipe_id=recipe.id,
            step_no=step["step_no"],
            description=step["description"],
            duration_seconds=step["duration_seconds"],
        )
        session.add(recipe_step)

    return recipe.name


async def main():
    """主函数"""
    print("=== 开始导入 HowToCook 菜谱数据 ===\n")

    # 查找所有 Markdown 文件
    md_files = list(HOWTOCOOK_PATH.glob("dishes/**/*.md"))
    print(f"找到 {len(md_files)} 个菜谱文件\n")

    # 创建数据库引擎
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 确保表存在
    async with engine.begin() as conn:
        # 检查 recipes 表是否存在
        result = await conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'recipes'
            )
        """))
        exists = result.scalar()
        if not exists:
            print("错误：数据库表不存在，请先运行数据库迁移")
            return

    # 统计
    total = 0
    success = 0
    failed = 0
    skipped = 0

    async with async_session() as session:
        for md_file in md_files:
            total += 1

            # 解析
            recipe_data = parse_markdown(md_file)
            if not recipe_data:
                skipped += 1
                continue

            # 检查是否已存在（通过菜名）
            result = await session.execute(
                text("SELECT id FROM recipes WHERE name = :name AND source_type = 'howtocook'"),
                {"name": recipe_data["name"]}
            )
            if result.fetchone():
                skipped += 1
                print(f"跳过 (已存在): {recipe_data['name']}")
                continue

            try:
                # 导入
                name = await import_recipe(session, recipe_data)
                await session.commit()
                success += 1
                print(f"导入成功：{name}")
            except Exception as e:
                await session.rollback()
                failed += 1
                print(f"导入失败 {recipe_data.get('name', md_file)}: {e}")

            # 每 50 条打印统计
            if total % 50 == 0:
                print(f"\n--- 进度：{total}/{len(md_files)} (成功:{success} 失败:{failed} 跳过:{skipped}) ---\n")

    print(f"\n=== 导入完成 ===")
    print(f"总计：{total} 个文件")
    print(f"成功：{success} 个菜谱")
    print(f"失败：{failed} 个")
    print(f"跳过：{skipped} 个（已存在或无法解析）")


if __name__ == "__main__":
    asyncio.run(main())
