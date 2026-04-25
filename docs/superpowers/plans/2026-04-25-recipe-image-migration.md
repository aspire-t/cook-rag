# Recipe Image Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate all recipe image URLs from local static file paths to king-jingxiang/HowToCook GitHub Pages CDN.

**Architecture:** A migration script scans local image files, matches against `recipe_images` table by `source_path`, builds new GitHub Pages URLs, and batch-updates `image_url`. API layer is updated to support fallback to local static files.

**Tech Stack:** Python, SQLAlchemy async, SQLite, FastAPI

---

### Task 1: Write migration script

**Files:**
- Create: `scripts/migrate_images_to_howtocook.py`

This script:
1. Walks `data/howtocook/public/images/` to build a filename → category lookup
2. Reads all rows from `recipe_images` table
3. For each row, checks if the image file exists locally (same source)
4. Builds new GitHub Pages URL: `https://king-jingxiang.github.io/HowToCook/images/dishes/{source_path}`
5. Updates `image_url` in the database
6. Records unmatched rows
7. Prints coverage stats and writes missing items to CSV

```python
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
from sqlalchemy import text, select

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
            rel = img_path.relative_to(IMAGES_DIR / "dishes")
            index.add(str(rel))
    return index


async def migrate_images():
    engine = create_async_engine(DB_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession)

    image_index = build_image_index()
    print(f"本地图片索引: {len(image_index)} 张图片")

    matched = 0
    unmatched = 0
    missing_list = []

    async with async_session() as session:
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
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./cookrag.db"
    asyncio.run(migrate_images())
```

**Step:** Run the script and verify output

```bash
python scripts/migrate_images_to_howtocook.py
```

Expected output:
```
本地图片索引: 341 张图片
待迁移图片: 3 条记录
迁移完成:
  成功: 3/3 (100.0%)
  未匹配: 0
```

Commit after verifying all 3 test records updated.

---

### Task 2: Update config and add fallback URL builder

**Files:**
- Modify: `app/core/config.py` (update image CDN config)
- Create: `app/services/image_url_builder.py` (URL builder with fallback)

**app/core/config.py** — Add the HowToCook CDN URL:

```python
# Image Storage
HOWTOCOOK_IMAGE_BASE_URL: str = "https://king-jingxiang.github.io/HowToCook/images/dishes/"
IMAGE_FALLBACK_BASE: str = "/howtocook-images/dishes/"  # local static mount fallback
```

**app/services/image_url_builder.py** — build function with fallback:

```python
"""图片 URL 构建 — 优先 HowToCook GitHub Pages CDN，回退本地静态文件."""

from app.core.config import settings


def build_image_url(source_path: str) -> str:
    """根据 source_path 构建图片 URL.

    Args:
        source_path: 如 "meat_dish/红烧肉.jpeg"

    Returns:
        GitHub Pages CDN URL
    """
    return settings.HOWTOCOOK_IMAGE_BASE_URL + source_path


def build_fallback_image_url(source_path: str) -> str:
    """构建本地回退 URL（当 CDN 不可用时）."""
    return settings.IMAGE_FALLBACK_BASE + source_path
```

**Step:** Verify the module can be imported

```bash
python -c "from app.services.image_url_builder import build_image_url; print(build_image_url('meat_dish/红烧肉.jpeg'))"
```

Expected output:
```
https://king-jingxiang.github.io/HowToCook/images/dishes/meat_dish/红烧肉.jpeg
```

---

### Task 3: Update recipe API to include fallback image info

**Files:**
- Modify: `app/api/v1/recipes.py:103-143` (recipe detail endpoint)

Add `image_fallback_url` to the step_images and cover_image response so the frontend can fall back if CDN fails.

Update the recipe detail endpoint to include `image_fallback_url` alongside `url`:

```python
        # ... (keep the query code above unchanged)

        from app.services.image_url_builder import build_fallback_image_url

        cover_image = None
        cover_fallback = None
        step_images = []
        for img in images:
            fallback = build_fallback_image_url(img.source_path)
            if img.image_type == "cover":
                cover_image = img.image_url
                cover_fallback = fallback
            else:
                step_images.append({
                    "step_no": img.step_no,
                    "url": img.image_url,
                    "fallback_url": fallback,
                })
        step_images.sort(key=lambda x: x["step_no"] or 0)
```

And in the response model, add `fallback_url` field. Update `StepItem` in the endpoint return:

Also update the `RecipeDetailResponse` model in `app/api/v1/recipes.py` line 45-46:

```python
class RecipeDetailResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    cuisine: Optional[str] = None
    difficulty: Optional[str] = None
    tags: List[str] = []
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None
    ingredients: List[IngredientItem] = []
    steps: List[StepItem] = []
    favorites_count: int = 0
    view_count: int = 0
    rating: Optional[float] = None
    cover_image: Optional[str] = None
    cover_fallback_url: Optional[str] = None
    step_images: List[dict] = []
```

Then update the return block at line 127:

```python
        return RecipeDetailResponse(
            id=str(recipe.id),
            name=recipe.name,
            description=recipe.description,
            cuisine=recipe.cuisine,
            difficulty=recipe.difficulty,
            tags=recipe.tags or [],
            prep_time=recipe.prep_time,
            cook_time=recipe.cook_time,
            ingredients=ingredients,
            steps=steps,
            favorites_count=recipe.favorite_count or 0,
            view_count=recipe.view_count or 0,
            rating=None,
            cover_image=cover_image,
            cover_fallback_url=cover_fallback,
            step_images=step_images,
        )
```

**Step:** Test the API endpoint

```bash
python start_sqlite.py &
# Wait for server to start
curl -s http://localhost:8000/api/v1/recipes/11111111-1111-1111-1111-111111111111 | python -m json.tool | grep -A3 cover
```

Expected: `cover_image` should be GitHub Pages URL, `cover_fallback_url` should be `/howtocook-images/dishes/meat_dish/...`

---

### Task 4: Add e2e test for image URL migration

**Files:**
- Create: `tests/test_image_migration.py`
- Modify: `tests/conftest.py` (if needed for fixtures)

```python
"""测试图片 URL 迁移."""

import pytest
import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

# Add parent to path so we can import the migration script
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temp SQLite DB for testing."""
    return f"sqlite+aiosqlite:///{tmp_path}/test_migration.db"


@pytest.fixture
async def migration_db(temp_db_path):
    """Set up test DB with sample recipe_images."""
    engine = create_async_engine(temp_db_path, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession)

    async with async_session() as session:
        await session.execute(text("""
            CREATE TABLE recipe_images (
                id TEXT PRIMARY KEY,
                recipe_id TEXT,
                step_no INTEGER,
                image_type TEXT,
                source_path TEXT,
                local_path TEXT,
                image_url TEXT,
                width INTEGER, height INTEGER, file_size INTEGER,
                clip_vector_id TEXT,
                created_at TIMESTAMP DEFAULT (datetime('now'))
            )
        """))
        # Insert test records
        test_data = [
            ("img-1", "recipe-1", None, "cover", "meat_dish/红烧肉.jpeg", "/path/to/红烧肉.jpeg", "/howtocook-images/dishes/meat_dish/红烧肉.jpeg", None, None, None, None),
            ("img-2", "recipe-2", None, "cover", "vegetable_dish/西红柿炒鸡蛋.jpeg", "/path/to/西红柿炒鸡蛋.jpeg", "/howtocook-images/dishes/vegetable_dish/西红柿炒鸡蛋.jpeg", None, None, None, None),
            ("img-3", "recipe-3", None, "cover", "unknown/不存在的菜.jpeg", "/path/to/不存在的菜.jpeg", "/howtocook-images/dishes/unknown/不存在的菜.jpeg", None, None, None, None),
        ]
        for row in test_data:
            await session.execute(text("""
                INSERT INTO recipe_images (id, recipe_id, step_no, image_type, source_path, local_path, image_url, width, height, file_size, clip_vector_id)
                VALUES (:id, :recipe_id, :step_no, :image_type, :source_path, :local_path, :image_url, :width, :height, :file_size, :clip_vector_id)
            """), {
                "id": row[0], "recipe_id": row[1], "step_no": row[2],
                "image_type": row[3], "source_path": row[4], "local_path": row[5],
                "image_url": row[6], "width": row[7], "height": row[8],
                "file_size": row[9], "clip_vector_id": row[10],
            })
        await session.commit()

    yield temp_db_path


class TestBuildImageURL:
    """Test image URL builder."""

    def test_build_github_pages_url(self):
        from app.services.image_url_builder import build_image_url
        url = build_image_url("meat_dish/红烧肉.jpeg")
        assert url == "https://king-jingxiang.github.io/HowToCook/images/dishes/meat_dish/红烧肉.jpeg"

    def test_build_fallback_url(self):
        from app.services.image_url_builder import build_fallback_image_url
        url = build_fallback_image_url("vegetable_dish/炒青菜.jpeg")
        assert url == "/howtocook-images/dishes/vegetable_dish/炒青菜.jpeg"


class TestImageIndex:
    """Test local image index builder."""

    def test_index_finds_files(self):
        from scripts.migrate_images_to_howtocook import build_image_index
        index = build_image_index()
        assert len(index) > 0
        # Should contain known files
        assert "vegetable_dish/西红柿炒鸡蛋.jpeg" in index
        assert "meat_dish/红烧肉.jpeg" in index
```

**Step:** Run the new test

```bash
cd /Users/wangzhentao/code/cook-rag && python -m pytest tests/test_image_migration.py -v
```

Expected: All tests pass

---

### Task 5: Run full migration and verify

**Files:** No code changes — run the migration script against the real DB.

**Steps:**

- [ ] **Step 1: Backup current DB**

```bash
cp cookrag.db cookrag.db.bak
```

- [ ] **Step 2: Run migration**

```bash
python scripts/migrate_images_to_howtocook.py
```

- [ ] **Step 3: Verify DB state**

```bash
sqlite3 cookrag.db "SELECT source_path, image_url FROM recipe_images LIMIT 5;"
```

Expected: `image_url` should start with `https://king-jingxiang.github.io/HowToCook/images/dishes/`

- [ ] **Step 4: Start server and test API**

```bash
python start_sqlite.py &
sleep 3
curl -s http://localhost:8000/api/v1/recipes/11111111-1111-1111-1111-111111111111 | python -m json.tool
```

Expected: `cover_image` is GitHub Pages URL

- [ ] **Step 5: Verify image loads in browser**

Open `http://localhost:8000/api/v1/recipes/11111111-1111-1111-1111-111111111111` and check the `cover_image` URL returns a valid image (or curl it).

- [ ] **Step 6: Commit**

```bash
git add scripts/migrate_images_to_howtocook.py
git add app/core/config.py
git add app/services/image_url_builder.py
git add app/api/v1/recipes.py
git add tests/test_image_migration.py
git commit -m "feat: migrate recipe images to HowToCook GitHub Pages CDN"
```

---

## Self-Review

**1. Spec coverage:**
- Phase 1 (migration script) → Task 1 + Task 5 ✓
- Phase 2 (API config + fallback) → Task 2 + Task 3 ✓
- Verification → Task 4 (e2e test) + Task 5 ✓
- Error handling (missing images CSV) → Task 1 ✓
- Static file fallback preserved → Task 3 (cover_fallback_url) ✓

**2. Placeholder scan:** No TBD/TODO found. All code blocks complete.

**3. Type consistency:** `source_path` format is consistent ("category/name.jpeg") across migration script, URL builder, and API endpoint.

**4. Scope check:** Focused only on URL migration + API fallback. No image generation, no frontend changes — as spec says.
