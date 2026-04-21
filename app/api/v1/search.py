"""搜索和推荐 API 路由."""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.hybrid_search import get_hybrid_search_service
from app.services.rerank_service import rerank_candidates
from app.core.auth import get_current_user
from app.models.user import User

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    filters: Optional[dict] = None
    top_k: int = 10
    use_hybrid: bool = True
    use_rerank: bool = True


class SearchRecipeResult(BaseModel):
    recipe_id: str
    score: float
    name: Optional[str] = None
    description: Optional[str] = None
    cuisine: Optional[str] = None
    difficulty: Optional[str] = None
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None


class SearchResponse(BaseModel):
    query: str
    results: List[SearchRecipeResult]
    total: int
    source: str


class RecommendRequest(BaseModel):
    user_id: Optional[str] = None
    context: Optional[str] = None
    top_k: int = 5


class RecommendRecipeResult(BaseModel):
    recipe_id: str
    score: float
    reason: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    cuisine: Optional[str] = None
    difficulty: Optional[str] = None


class RecommendResponse(BaseModel):
    results: List[RecommendRecipeResult]
    source: str


@router.post("/search", response_model=SearchResponse)
async def search_recipes(
    request: SearchRequest,
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    搜索菜谱.

    支持：
    - 关键词搜索
    - 混合检索（ES BM25 + Qdrant 向量）
    - Rerank 重排序（个性化加权）
    """
    try:
        search_service = get_hybrid_search_service()

        results = await search_service.search(
            query=request.query,
            filters=request.filters,
            use_hybrid=request.use_hybrid,
            user_prefs=current_user.taste_prefs if current_user else None,
        )

        search_results = [
            SearchRecipeResult(
                recipe_id=r.get("recipe_id") or r.get("id", ""),
                score=r.get("rrf_score") or r.get("score", 0),
                name=r.get("payload", {}).get("name"),
                description=r.get("payload", {}).get("description"),
                cuisine=r.get("payload", {}).get("cuisine"),
                difficulty=r.get("payload", {}).get("difficulty"),
                prep_time=r.get("payload", {}).get("prep_time"),
                cook_time=r.get("payload", {}).get("cook_time"),
            )
            for r in results[: request.top_k]
        ]

        return SearchResponse(
            query=request.query,
            results=search_results,
            total=len(search_results),
            source="hybrid" if request.use_hybrid else "es",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败：{str(e)}")


@router.post("/recommend", response_model=RecommendResponse)
async def recommend_recipes(
    request: RecommendRequest,
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    个性化推荐菜谱.

    根据用户偏好和历史行为进行推荐。
    """
    try:
        user_prefs = None
        if current_user and current_user.taste_prefs:
            user_prefs = current_user.taste_prefs

        query = request.context or "推荐菜谱"
        search_service = get_hybrid_search_service()

        results = await search_service.search(
            query=query,
            filters=None,
            use_hybrid=True,
            user_prefs=user_prefs,
        )

        if user_prefs:
            results = await rerank_candidates(
                query=query,
                candidates=results,
                user_prefs=user_prefs,
                top_k=request.top_k,
            )

        def generate_reason(result: dict) -> str:
            reasons = []
            payload = result.get("payload", result)
            if user_prefs and payload.get("cuisine") in user_prefs.get("preferred_cuisines", []):
                reasons.append(f"匹配您喜欢的{payload.get('cuisine')}菜系")
            if not reasons:
                reasons.append("根据您的浏览历史推荐")
            return "; ".join(reasons)

        recommend_results = [
            RecommendRecipeResult(
                recipe_id=r.get("recipe_id") or r.get("id", ""),
                score=r.get("score") or r.get("rrf_score", 0),
                reason=generate_reason(r),
                name=r.get("payload", {}).get("name"),
                description=r.get("payload", {}).get("description"),
                cuisine=r.get("payload", {}).get("cuisine"),
                difficulty=r.get("payload", {}).get("difficulty"),
            )
            for r in results[: request.top_k]
        ]

        return RecommendResponse(
            results=recommend_results,
            source="hybrid_rerank" if user_prefs else "hybrid",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推荐失败：{str(e)}")
