#!/usr/bin/env python3
"""迁移菜谱图片至 king-jingxiang/HowToCook GitHub Pages CDN.

流程:
1. 扫描本地 data/howtocook/public/images/ 建立文件名索引
2. 匹配 recipe_images 表的 source_path
3. 构建新 GitHub Pages URL 并更新 image_url
4. 输出覆盖率统计
"""

import asyncio
import os
import csv
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

IMAGES_DIR = Path(__file__).parent.parent / "data" / "howtocook" / "public" / "images"
GITHUB_PAGES_BASE = "https://king-jingxiang.github.io/HowToCook/images/dishes/"
DB_URL = "sqlite+aiosqlite:///./cookrag.db"


def build_image_index():
    """扫描本地图片目录，返回 {source_path: True} 的集合."""
    index = set()
    if not IMAGES_DIR.exists():
        return index
    for img_path in IMAGES_DIR.rglob("*"):
        if img_path.is_file() and img_path.suffix.lower() in (".jpeg", ".jpg", ".png", ".webp"):
            # source_path 格式: "meat_dish/红烧肉.jpeg"
            try:
                rel = img_path.relative_to(IMAGES_DIR / "dishes")
                index.add(str(rel))
            except ValueError:
                pass  # skip files outside the dishes subdirectory
    return index


async def migrate_images():
    engine = create_async_engine(DB_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession)

    image_index = build_image_index()
    print(f"本地图片索引: {len(image_index)} 张图片")

    matched = 0
    unmatched = 0
    missing_list = []

    try:
        async with async_session() as session:
            try:
                rows = await session.execute(
                    text("SELECT id, source_path, image_url FROM recipe_images")
                )
                rows = rows.fetchall()
                print(f"待迁移图片: {len(rows)} 条记录")

                for row in rows:
                    img_id, source_path, old_url = row
                    if source_path in image_index:
                        new_url = GITHUB_PAGES_BASE + source_path
                        await session.execute(
                            text("UPDATE recipe_images SET image_url = :url WHERE id = :id"),
                            {"url": new_url, "id": str(img_id)},
                        )
                        matched += 1
                    else:
                        unmatched += 1
                        missing_list.append({
                            "id": str(img_id),
                            "source_path": source_path,
                            "old_url": old_url,
                        })

                await session.commit()
            except Exception as e:
                await session.rollback()
                raise RuntimeError(f"迁移过程中出错: {e}") from e
    finally:
        await engine.dispose()

    # 输出统计
    total = matched + unmatched
    coverage = (matched / total * 100) if total > 0 else 0
    print(f"\n迁移完成:")
    print(f"  成功: {matched}/{total} ({coverage:.1f}%)")
    print(f"  未匹配: {unmatched}")

    # 写入缺失列表
    if missing_list:
        missing_csv = Path(__file__).parent / "missing_images.csv"
        with open(missing_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "source_path", "old_url"])
            writer.writeheader()
            writer.writerows(missing_list)
        print(f"  缺失列表已写入: {missing_csv}")


if __name__ == "__main__":
    asyncio.run(migrate_images())
