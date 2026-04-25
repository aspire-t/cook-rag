"""图片 API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import aiohttp
import base64
from io import BytesIO
from PIL import Image

from app.core.database import get_db
from app.models.recipe_image import RecipeImage
from app.api.schemas import (
    RecipeImageResponse,
    RecipeImagesResponse,
    ImageSearchRequest,
    ImageSearchResponse,
)
from app.services.clip_service import get_clip_service
from app.services.qdrant_service import get_qdrant_service

router = APIRouter()


@router.get(
    "/recipes/{recipe_id}/images",
    response_model=RecipeImagesResponse,
    summary="获取菜谱图片"
)
async def get_recipe_images(
    recipe_id: str,
    db: AsyncSession = Depends(get_db)
) -> RecipeImagesResponse:
    """获取菜谱的所有图片（封面 + 步骤图）。"""
    from uuid import UUID

    # 验证 UUID 格式
    try:
        recipe_uuid = UUID(recipe_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的菜谱 ID 格式")

    # 查询图片
    result = await db.execute(
        select(RecipeImage)
        .where(RecipeImage.recipe_id == recipe_uuid)
        .order_by(RecipeImage.step_no.nullsfirst(), RecipeImage.id)
    )
    images = result.scalars().all()

    if not images:
        raise HTTPException(status_code=404, detail="图片不存在")

    # 分离封面图和步骤图
    cover = None
    steps = []
    for img in images:
        if img.image_type == "cover":
            cover = img
        else:
            steps.append(img)

    # 按 step_no 排序步骤图
    steps.sort(key=lambda x: x.step_no if x.step_no is not None else 0)

    return RecipeImagesResponse(
        recipe_id=str(recipe_id),
        cover=RecipeImageResponse(
            id=str(cover.id),
            step_no=cover.step_no,
            image_type=cover.image_type,
            image_url=cover.image_url,
            width=cover.width,
            height=cover.height,
            file_size=cover.file_size
        ) if cover else None,
        steps=[
            RecipeImageResponse(
                id=str(img.id),
                step_no=img.step_no,
                image_type=img.image_type,
                image_url=img.image_url,
                width=img.width,
                height=img.height,
                file_size=img.file_size
            )
            for img in steps
        ]
    )


@router.post(
    "/search/image",
    response_model=ImageSearchResponse,
    summary="以图搜菜/多模态搜索"
)
async def search_by_image(
    request: ImageSearchRequest,
    db: AsyncSession = Depends(get_db)
) -> ImageSearchResponse:
    """多模态搜索：支持图片搜索和文本搜图片。

    - **image_url**: 图片 URL（可选）
    - **image_base64**: Base64 图片（可选，与 image_url 二选一）
    - **text_query**: 文本查询（可选，可与图片组合）
    - **limit**: 返回数量（默认 10）

    搜索模式：
    1. 纯图片搜索：以图搜菜
    2. 纯文本搜索：文本搜图片
    3. 组合搜索：图片 + 文本（例如：搜索相似图片但限定菜系）
    """
    clip_service = get_clip_service()
    qdrant_service = get_qdrant_service()

    # 获取查询向量
    query_vector = None
    query_type = "text"

    if request.image_url or request.image_base64:
        query_type = "image"
        # 加载图片
        if request.image_base64:
            img_data = base64.b64decode(request.image_base64)
            img = Image.open(BytesIO(img_data)).convert("RGB")
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(request.image_url) as resp:
                    img_data = await resp.read()
            img = Image.open(BytesIO(img_data)).convert("RGB")

        # 获取向量
        query_vector = clip_service.get_image_embedding(img)
    elif request.text_query:
        # 文本向量
        query_vector = clip_service.get_text_embedding(request.text_query)
    else:
        raise HTTPException(
            status_code=400,
            detail="需要提供 image_url、image_base64 或 text_query"
        )

    # 搜索
    results = qdrant_service.search_image_vector(
        query_vector=query_vector,
        limit=request.limit
    )

    return ImageSearchResponse(
        query_type=query_type,
        results=results
    )


@router.post(
    "/search/multimodal",
    response_model=ImageSearchResponse,
    summary="多模态联合搜索"
)
async def search_multimodal(
    image_url: Optional[str] = None,
    image_base64: Optional[str] = None,
    text_query: Optional[str] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
) -> ImageSearchResponse:
    """多模态联合搜索：同时使用文本和图片向量进行 RRF 融合排序。

    支持 form-data 格式上传：
    - **image_url**: 图片 URL（可选）
    - **image_base64**: Base64 图片（可选）
    - **text_query**: 文本查询（可选）
    - **limit**: 返回数量
    """
    clip_service = get_clip_service()

    vectors = {}

    # 获取图片向量
    if image_url or image_base64:
        if image_base64:
            img_data = base64.b64decode(image_base64)
            img = Image.open(BytesIO(img_data)).convert("RGB")
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    img_data = await resp.read()
            img = Image.open(BytesIO(img_data)).convert("RGB")

        vectors["image"] = clip_service.get_image_embedding(img)

    # 获取文本向量
    if text_query:
        vectors["text"] = clip_service.get_text_embedding(text_query)

    if not vectors:
        raise HTTPException(
            status_code=400,
            detail="需要提供图片或文本查询"
        )

    # TODO: 实现多向量 RRF 融合搜索
    # 目前先使用第一个向量
    query_vector = list(vectors.values())[0]
    query_type = "image" if "image" in vectors else "text"

    qdrant_service = get_qdrant_service()
    results = qdrant_service.search_image_vector(
        query_vector=query_vector,
        limit=limit
    )

    return ImageSearchResponse(
        query_type=query_type,
        results=results
    )
