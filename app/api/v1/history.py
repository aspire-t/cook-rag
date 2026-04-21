"""搜索历史 API."""

import uuid
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.search_history import SearchHistory
from app.api.schemas import APIResponse

router = APIRouter()


class SearchHistoryItem(BaseModel):
    id: str
    query: str
    result_count: int
    clicked_recipe_id: Optional[str] = None
    created_at: datetime


class SearchHistoryResponse(BaseModel):
    total: int
    history: List[SearchHistoryItem]


def get_session_id(request: Request) -> str:
    """从请求头或 Cookie 获取 session_id."""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id


@router.get("/search-history", response_model=SearchHistoryResponse)
async def get_search_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user),
    session_id: str = Depends(get_session_id),
    db: AsyncSession = Depends(get_db),
):
    """
    获取搜索历史.

    支持：
    - 认证用户：按 user_id 查询
    - 匿名用户：按 session_id 查询
    """
    try:
        offset = (page - 1) * page_size

        # 确定查询条件
        if current_user:
            # 认证用户优先使用 user_id
            where_clause = SearchHistory.user_id == str(current_user.id)
        else:
            # 匿名用户使用 session_id
            where_clause = SearchHistory.session_id == session_id

        # 查询历史
        result = await db.execute(
            select(SearchHistory)
            .where(where_clause)
            .order_by(SearchHistory.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        rows = result.scalars().all()

        # 查询总数
        count_result = await db.execute(
            select(sa_func.count(SearchHistory.id))
            .where(where_clause)
        )
        total = count_result.scalar() or 0

        history = [
            SearchHistoryItem(
                id=row.id,
                query=row.query,
                result_count=row.result_count or 0,
                clicked_recipe_id=row.clicked_recipe_id,
                created_at=row.created_at,
            )
            for row in rows
        ]

        return SearchHistoryResponse(total=total, history=history)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取搜索历史失败：{str(e)}")


class RecordSearchRequest(BaseModel):
    query: str
    filters: Optional[dict] = None
    result_count: int = 0


@router.post("/search-history", response_model=APIResponse)
async def record_search(
    request: RecordSearchRequest,
    current_user: Optional[User] = Depends(get_current_user),
    session_id: str = Depends(get_session_id),
    db: AsyncSession = Depends(get_db),
):
    """
    记录搜索历史.

    支持：
    - 认证用户：关联 user_id
    - 匿名用户：关联 session_id
    """
    try:
        import json
        from datetime import datetime

        search_history = SearchHistory(
            id=str(uuid.uuid4()),
            user_id=str(current_user.id) if current_user else None,
            session_id=session_id if not current_user else None,
            query=request.query,
            filters=json.dumps(request.filters) if request.filters else None,
            result_count=request.result_count,
        )

        db.add(search_history)
        await db.commit()

        return APIResponse(message="搜索历史记录成功")

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"记录搜索历史失败：{str(e)}")


class RecordClickRequest(BaseModel):
    search_history_id: str
    recipe_id: str


@router.post("/search-history/click", response_model=APIResponse)
async def record_click(
    request: RecordClickRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    记录点击行为（CTR 数据采集）.

    用于后续分析搜索质量和推荐优化。
    """
    try:
        # 更新搜索历史
        result = await db.execute(
            select(SearchHistory).where(SearchHistory.id == request.search_history_id)
        )
        search_history = result.scalar_one_or_none()

        if not search_history:
            raise HTTPException(status_code=404, detail="搜索历史记录不存在")

        search_history.clicked_recipe_id = request.recipe_id
        await db.commit()

        return APIResponse(message="点击记录成功")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"记录点击失败：{str(e)}")
