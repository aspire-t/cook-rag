"""UGC 菜谱上传 API."""

import re
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.recipe import Recipe
from app.models.ingredient import RecipeIngredient
from app.models.step import RecipeStep
from app.api.schemas import APIResponse

router = APIRouter()


def parse_markdown(markdown: str) -> dict:
    """
    解析 Markdown 菜谱内容.

    支持格式:
    - # 菜名
    - ## 简介/描述
    - ## 食材
    - ## 步骤
    - ## 标签

    返回结构化数据。
    """
    result = {
        "name": "",
        "description": "",
        "ingredients": [],
        "steps": [],
        "tags": [],
    }

    lines = markdown.split("\n")
    current_section = None
    current_ingredient = ""
    current_step = ""
    step_number = 0

    for line in lines:
        line = line.strip()

        # 检测章节标题
        if line.startswith("## "):
            # 保存之前的内容
            if current_section == "ingredients" and current_ingredient:
                result["ingredients"].append(current_ingredient)
                current_ingredient = ""
            elif current_section == "steps" and current_step:
                step_number += 1
                result["steps"].append({"step_number": step_number, "description": current_step})
                current_step = ""

            section_title = line[3:].lower()
            if "食材" in section_title or "ingredient" in section_title:
                current_section = "ingredients"
            elif "步骤" in section_title or "step" in section_title or "做法" in section_title:
                current_section = "steps"
            elif "标签" in section_title or "tag" in section_title:
                current_section = "tags"
            else:
                current_section = None
            continue

        # 检测一级标题（菜名）
        if line.startswith("# ") and not result["name"]:
            result["name"] = line[2:].strip()
            current_section = None
            continue

        # 处理内容
        if current_section == "ingredients":
            # 食材行通常以 - 或 * 开头
            if line.startswith("- ") or line.startswith("* "):
                if current_ingredient:
                    result["ingredients"].append(current_ingredient)
                current_ingredient = line[2:].strip()
            elif line and current_ingredient:
                current_ingredient += " " + line

        elif current_section == "steps":
            # 步骤行可能以数字开头或直接描述
            step_match = re.match(r"^(?:\d+[.、]\s*)?(.+)", line)
            if step_match:
                if current_step:
                    step_number += 1
                    result["steps"].append({"step_number": step_number, "description": current_step})
                current_step = step_match.group(1)
            elif line:
                current_step += " " + line

        elif current_section == "tags":
            if line.startswith("- ") or line.startswith("* "):
                tag = line[2:].strip()
                if tag:
                    result["tags"].append(tag)
            elif line:
                # 逗号分隔的标签
                tags = [t.strip() for t in line.split(",") if t.strip()]
                result["tags"].extend(tags)

    # 保存最后的内容
    if current_section == "ingredients" and current_ingredient:
        result["ingredients"].append(current_ingredient)
    elif current_section == "steps" and current_step:
        step_number += 1
        result["steps"].append({"step_number": step_number, "description": current_step})

    # 解析描述（简介通常在第一个 ## 之前，# 之后）
    if not result["description"]:
        # 简单处理：如果没有专门的描述章节，使用前几行作为描述
        pass

    return result


@router.post("/recipes", response_model=APIResponse)
async def upload_recipe(
    name: str = Form(..., description="菜谱名称"),
    markdown_content: str = Form(..., description="Markdown 格式的菜谱内容"),
    cuisine: Optional[str] = Form(None, description="菜系"),
    difficulty: Optional[str] = Form(None, description="难度：easy/medium/hard"),
    prep_time: Optional[int] = Form(None, description="准备时间（分钟）"),
    cook_time: Optional[int] = Form(None, description="烹饪时间（分钟）"),
    servings: Optional[int] = Form(1, description="几人份"),
    tags: Optional[str] = Form(None, description="标签，逗号分隔"),
    images: Optional[List[UploadFile]] = File(None, description="菜谱图片"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传 UGC 菜谱.

    功能:
    - Markdown 解析：自动解析食材、步骤、标签
    - 图片上传：支持多张图片
    - 先发后审：新菜谱状态为 pending，审核通过后公开

    要求:
    - 需要用户认证
    - 菜名和 Markdown 内容必填
    """
    try:
        # 解析 Markdown 内容
        parsed = parse_markdown(markdown_content)

        # 使用表单 name 优先，否则使用 Markdown 解析的菜名
        recipe_name = name if name else parsed.get("name", "")
        if not recipe_name:
            raise HTTPException(status_code=400, detail="菜谱名称不能为空")

        # 解析标签
        recipe_tags = []
        if tags:
            recipe_tags = [t.strip() for t in tags.split(",") if t.strip()]
        if parsed.get("tags"):
            recipe_tags.extend(parsed["tags"])
        # 去重
        recipe_tags = list(dict.fromkeys(recipe_tags))

        # 创建菜谱
        recipe_id = uuid.uuid4()
        recipe = Recipe(
            id=recipe_id,
            name=recipe_name,
            description=parsed.get("description", ""),
            user_id=str(current_user.id),
            cuisine=cuisine,
            difficulty=difficulty,
            prep_time=prep_time,
            cook_time=cook_time,
            servings=servings,
            tags=recipe_tags,
            source_type="ugc",
            is_public=False,  # 审核通过前不公开
            audit_status="pending",  # 待审核状态
            view_count=0,
            favorite_count=0,
        )

        db.add(recipe)
        await db.flush()  # 获取 recipe_id

        # 创建食材
        for idx, ingredient_name in enumerate(parsed.get("ingredients", []), 1):
            ingredient = RecipeIngredient(
                id=str(uuid.uuid4()),
                recipe_id=str(recipe_id),
                name=ingredient_name,
                amount=None,
                unit=None,
                step_number=idx,
            )
            db.add(ingredient)

        # 创建步骤
        for step in parsed.get("steps", []):
            recipe_step = RecipeStep(
                id=str(uuid.uuid4()),
                recipe_id=str(recipe_id),
                step_number=step["step_number"],
                description=step["description"],
            )
            db.add(recipe_step)

        # 处理图片上传（MVP 阶段：仅保存元数据，实际存储在本地）
        image_paths = []
        if images:
            upload_dir = Path("data/uploads/recipes") / str(recipe_id)
            upload_dir.mkdir(parents=True, exist_ok=True)

            for image in images:
                if image.filename:
                    # 生成安全的文件名
                    ext = Path(image.filename).suffix.lower()
                    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
                        ext = ".jpg"
                    filename = f"{uuid.uuid4()}{ext}"
                    filepath = upload_dir / filename

                    # 保存图片
                    with open(filepath, "wb") as f:
                        content = await image.read()
                        f.write(content)

                    image_paths.append(f"/uploads/recipes/{recipe_id}/{filename}")

        # 保存图片路径到 tags 或单独字段（MVP 阶段简单处理）
        # TODO: 添加 recipe.images 字段

        await db.commit()

        return APIResponse(
            message="菜谱上传成功，等待审核通过后公开",
            data={"recipe_id": str(recipe_id), "audit_status": "pending"},
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"上传菜谱失败：{str(e)}")


@router.get("/recipes/{recipe_id}", response_model=dict)
async def get_ugc_recipe(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取 UGC 菜谱详情.

    仅菜谱所有者可以查看（包括 pending 状态的菜谱）。
    """
    try:
        result = await db.execute(
            select(Recipe).where(Recipe.id == recipe_id)
        )
        recipe = result.scalar_one_or_none()

        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")

        # 检查权限：只有所有者可以查看 pending 状态的菜谱
        if recipe.audit_status == "pending" and str(recipe.user_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="无权查看此菜谱")

        return {
            "id": str(recipe.id),
            "name": recipe.name,
            "description": recipe.description,
            "cuisine": recipe.cuisine,
            "difficulty": recipe.difficulty,
            "prep_time": recipe.prep_time,
            "cook_time": recipe.cook_time,
            "servings": recipe.servings,
            "tags": recipe.tags,
            "audit_status": recipe.audit_status,
            "rejected_reason": recipe.rejected_reason,
            "created_at": recipe.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取菜谱失败：{str(e)}")
