"""API Schema 定义."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


# ============ 搜索 API ============

class SearchRequest(BaseModel):
    """搜索请求."""
    query: str = Field(..., description="搜索关键词")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="过滤条件")
    top_k: int = Field(default=10, description="返回数量")
    use_hybrid: bool = Field(default=True, description="是否使用混合检索")
    use_rerank: bool = Field(default=True, description="是否启用重排序")


class SearchRecipeResult(BaseModel):
    """搜索菜谱结果."""
    recipe_id: str
    score: float
    name: Optional[str] = None
    description: Optional[str] = None
    cuisine: Optional[str] = None
    difficulty: Optional[str] = None
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None


class SearchResponse(BaseModel):
    """搜索响应."""
    query: str
    results: List[SearchRecipeResult]
    total: int
    source: str  # "hybrid", "es", "llm"


# ============ 推荐 API ============

class RecommendRequest(BaseModel):
    """推荐请求."""
    user_id: Optional[str] = Field(default=None, description="用户 ID")
    context: Optional[str] = Field(default=None, description="上下文（如当前浏览的菜谱）")
    top_k: int = Field(default=5, description="推荐数量")


class RecommendRecipeResult(BaseModel):
    """推荐菜谱结果."""
    recipe_id: str
    score: float
    reason: Optional[str] = None  # 推荐理由
    name: Optional[str] = None
    description: Optional[str] = None
    cuisine: Optional[str] = None
    difficulty: Optional[str] = None


class RecommendResponse(BaseModel):
    """推荐响应."""
    results: List[RecommendRecipeResult]
    source: str  # "collaborative", "content_based", "hybrid"


# ============ 菜谱详情 API ============

class IngredientItem(BaseModel):
    """食材项."""
    name: str
    amount: Optional[str] = None
    unit: Optional[str] = None
    sequence: int = 0


class StepItem(BaseModel):
    """步骤项."""
    step_no: int
    description: str
    duration_seconds: Optional[int] = None


class RecipeDetailResponse(BaseModel):
    """菜谱详情响应."""
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
    views_count: int = 0
    rating: Optional[float] = None


# ============ 通用响应 ============

class APIResponse(BaseModel):
    """通用 API 响应."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """错误响应."""
    success: bool = False
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
