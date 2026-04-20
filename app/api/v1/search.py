"""
搜索 API
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from app.services.search_service import SearchService


router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    filters: Optional[dict] = None
    limit: int = 10
    offset: int = 0


class SearchResponse(BaseModel):
    total: int
    recipes: List[dict]


@router.post("/", response_model=SearchResponse)
async def search_recipes(request: SearchRequest):
    """
    智能搜索菜谱

    支持：
    - 自然语言查询（"鸡肉和土豆做的菜"）
    - 多维度过滤（菜系、口味、时间等）
    """
    service = SearchService()
    results = await service.search(
        query=request.query,
        filters=request.filters,
        limit=request.limit,
        offset=request.offset,
    )
    return results


@router.get("/suggestions")
async def get_search_suggestions(q: str):
    """获取搜索建议"""
    # TODO: 实现搜索建议
    return {"suggestions": []}