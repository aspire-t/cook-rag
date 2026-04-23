"""API Schema 定义 - OpenAPI 文档增强."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# ============ 通用响应 ============

class APIResponse(BaseModel):
    """通用 API 响应."""
    code: int = Field(200, description="错误码，200 表示成功")
    message: str = Field("成功", description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "成功",
                "data": None
            }
        }


class ErrorResponse(BaseModel):
    """错误响应."""
    code: int = Field(description="错误码")
    message: str = Field(description="错误消息")
    data: Optional[Any] = Field(None, description="错误详情")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 4001,
                "message": "菜谱不存在",
                "data": None
            }
        }


# ============ 错误码说明 ============

ERROR_CODE_DESCRIPTIONS = {
    # 1xxx: 认证相关
    "1001": "无效的 Token",
    "1002": "Token 已过期",
    "1003": "缺少认证 Token",
    "1004": "用户名或密码错误",
    "1005": "用户不存在",
    "1006": "权限不足",
    # 2xxx: 通用/系统
    "2001": "内部服务器错误",
    "2002": "请求参数错误",
    "2003": "资源不存在",
    "2004": "服务暂时不可用",
    "2005": "请求频率超限",
    "2006": "数据验证失败",
    # 3xxx: 搜索/RAG
    "3001": "搜索失败",
    "3002": "RAG 处理失败",
    "3003": "缓存操作失败",
    # 4xxx: 菜谱/UGC
    "4001": "菜谱不存在",
    "4002": "已收藏该菜谱",
    "4003": "菜谱上传失败",
    "4004": "Markdown 解析失败",
    "4005": "文件大小超限",
    # 5xxx: 举报/审核
    "5001": "已举报过该菜谱",
    "5002": "举报失败",
    "5003": "菜谱已下架",
}

# ============ 搜索 API ============

class SearchRequest(BaseModel):
    """搜索请求."""
    query: str = Field(..., description="搜索关键词", min_length=1, max_length=100, example="红烧肉")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="过滤条件")
    top_k: int = Field(default=10, description="返回数量", ge=1, le=50)
    use_hybrid: bool = Field(default=True, description="是否使用混合检索")
    use_rerank: bool = Field(default=True, description="是否启用重排序")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "红烧肉",
                "filters": None,
                "top_k": 10,
                "use_hybrid": True,
                "use_rerank": True
            }
        }


class SearchRecipeResult(BaseModel):
    """搜索菜谱结果."""
    recipe_id: str = Field(..., description="菜谱 ID", example="550e8400-e29b-41d4-a716-446655440000")
    score: float = Field(..., description="相关度分数", example=0.95)
    name: Optional[str] = Field(None, description="菜名", example="红烧肉")
    description: Optional[str] = Field(None, description="简介", example="色泽红亮，肥而不腻")
    cuisine: Optional[str] = Field(None, description="菜系", example="川菜")
    difficulty: Optional[str] = Field(None, description="难度", example="medium")
    prep_time: Optional[int] = Field(None, description="准备时间 (分钟)", example=15)
    cook_time: Optional[int] = Field(None, description="烹饪时间 (分钟)", example=60)


class SearchResponse(BaseModel):
    """搜索响应."""
    query: str = Field(..., description="搜索词", example="红烧肉")
    results: List[SearchRecipeResult] = Field(default_factory=list, description="搜索结果")
    total: int = Field(..., description="总结果数", example=100)
    source: str = Field(..., description="来源", example="hybrid")
    duration_ms: float = Field(..., description="搜索耗时 (毫秒)", example=45.2)


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
    id: str = Field(..., description="菜谱 ID", example="550e8400-e29b-41d4-a716-446655440000")
    name: str = Field(..., description="菜名", example="红烧肉")
    description: Optional[str] = Field(None, description="简介", example="色泽红亮，肥而不腻")
    cuisine: Optional[str] = Field(None, description="菜系", example="川菜")
    difficulty: Optional[str] = Field(None, description="难度", example="medium")
    tags: List[str] = Field(default_factory=list, description="标签", example=["辣", "下饭", "经典"])
    prep_time: Optional[int] = Field(None, description="准备时间 (分钟)", example=15)
    cook_time: Optional[int] = Field(None, description="烹饪时间 (分钟)", example=60)
    ingredients: List[IngredientItem] = Field(default_factory=list, description="食材列表")
    steps: List[StepItem] = Field(default_factory=list, description="步骤列表")
    favorites_count: int = Field(0, description="收藏数", example=567)
    views_count: int = Field(0, description="浏览数", example=1234)
    rating: Optional[float] = Field(None, description="评分", example=4.5)
    is_public: bool = Field(True, description="是否公开")
    audit_status: str = Field("approved", description="审核状态")


# ============ 收藏 API ============

class FavoriteRequest(BaseModel):
    """收藏请求."""
    recipe_id: str = Field(..., description="菜谱 ID", example="550e8400-e29b-41d4-a716-446655440000")

    class Config:
        json_schema_extra = {
            "example": {
                "recipe_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class FavoriteItem(BaseModel):
    """收藏项."""
    id: str = Field(..., description="收藏 ID")
    recipe_id: str = Field(..., description="菜谱 ID")
    recipe_name: str = Field(..., description="菜名")
    created_at: datetime = Field(..., description="收藏时间")


class FavoritesResponse(BaseModel):
    """收藏列表响应."""
    total: int = Field(..., description="总数")
    favorites: List[FavoriteItem] = Field(default_factory=list, description="收藏列表")


# ============ 搜索历史 API ============

class SearchHistoryItem(BaseModel):
    """搜索历史项."""
    id: str = Field(..., description="历史记录 ID")
    query: str = Field(..., description="搜索词")
    result_count: int = Field(0, description="结果数量")
    clicked_recipe_id: Optional[str] = Field(None, description="点击的菜谱 ID")
    created_at: datetime = Field(..., description="搜索时间")


class SearchHistoryResponse(BaseModel):
    """搜索历史响应."""
    total: int = Field(..., description="总数")
    history: List[SearchHistoryItem] = Field(default_factory=list, description="历史列表")


class RecordSearchRequest(BaseModel):
    """记录搜索请求."""
    query: str = Field(..., description="搜索词", example="红烧肉")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    result_count: int = Field(0, description="结果数量", example=10)


class RecordClickRequest(BaseModel):
    """记录点击请求."""
    search_history_id: str = Field(..., description="搜索历史 ID", example="hist-123")
    recipe_id: str = Field(..., description="菜谱 ID", example="recipe-456")


# ============ UGC 上传 API ============

class UploadRecipeRequest(BaseModel):
    """上传菜谱请求."""
    name: str = Field(..., description="菜谱名称", min_length=1, max_length=100, example="我的红烧肉")
    markdown_content: str = Field(..., description="Markdown 格式内容")
    cuisine: Optional[str] = Field(None, description="菜系", example="川菜")
    difficulty: Optional[str] = Field(None, description="难度", example="medium")
    prep_time: Optional[int] = Field(None, description="准备时间 (分钟)", example=15)
    cook_time: Optional[int] = Field(None, description="烹饪时间 (分钟)", example=60)
    servings: int = Field(1, description="几人份", example=4)
    tags: Optional[str] = Field(None, description="标签，逗号分隔", example="辣，下饭，经典")


class UploadRecipeResponse(BaseModel):
    """上传菜谱响应."""
    code: int = Field(200, description="错误码")
    message: str = Field("菜谱上传成功，等待审核通过后公开", description="响应消息")
    data: Dict[str, Any] = Field(default_factory=dict, description="响应数据")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "菜谱上传成功，等待审核通过后公开",
                "data": {
                    "recipe_id": "550e8400-e29b-41d4-a716-446655440000",
                    "audit_status": "pending"
                }
            }
        }


# ============ 举报 API ============

class ReportRecipeRequest(BaseModel):
    """举报菜谱请求."""
    recipe_id: str = Field(..., description="菜谱 ID", example="550e8400-e29b-41d4-a716-446655440000")
    reason: str = Field(..., description="举报原因", min_length=10, max_length=1024, example="内容包含虚假宣传，误导用户")


class ReportRecipeResponse(BaseModel):
    """举报菜谱响应."""
    code: int = Field(200, description="错误码")
    message: str = Field(..., description="响应消息")
    data: Dict[str, Any] = Field(default_factory=dict, description="响应数据")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "举报成功，当前举报次数：3",
                "data": {
                    "report_id": "report-123",
                    "report_count": 3,
                    "auto_offline": False
                }
            }
        }


# ============ 认证 API ============


# ============ 图片 API ============

class RecipeImageResponse(BaseModel):
    """图片响应."""
    id: str = Field(..., description="图片 ID")
    step_no: Optional[int] = Field(None, description="步骤编号，封面图为 None")
    image_type: str = Field(..., description="图片类型", example="cover")
    image_url: str = Field(..., description="图片 URL", example="https://cdn.example.com/recipes/cover/xxx.jpg")
    width: Optional[int] = Field(None, description="图片宽度", example=800)
    height: Optional[int] = Field(None, description="图片高度", example=600)
    file_size: Optional[int] = Field(None, description="文件大小（字节）", example=102400)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "step_no": None,
                "image_type": "cover",
                "image_url": "https://cdn.example.com/recipes/cover/xxx.jpg",
                "width": 800,
                "height": 600,
                "file_size": 102400
            }
        }


class RecipeImagesResponse(BaseModel):
    """图片列表响应."""
    recipe_id: str = Field(..., description="菜谱 ID")
    cover: Optional[RecipeImageResponse] = Field(None, description="封面图")
    steps: List[RecipeImageResponse] = Field(default_factory=list, description="步骤图列表")

    class Config:
        json_schema_extra = {
            "example": {
                "recipe_id": "550e8400-e29b-41d4-a716-446655440000",
                "cover": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "step_no": None,
                    "image_type": "cover",
                    "image_url": "https://cdn.example.com/recipes/cover/xxx.jpg",
                    "width": 800,
                    "height": 600,
                    "file_size": 102400
                },
                "steps": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440002",
                        "step_no": 1,
                        "image_type": "step",
                        "image_url": "https://cdn.example.com/recipes/steps/xxx_1.jpg",
                        "width": 800,
                        "height": 600,
                        "file_size": 81920
                    }
                ]
            }
        }


class ImageSearchRequest(BaseModel):
    """图片搜索请求."""
    image_url: Optional[str] = Field(None, description="图片 URL", example="https://example.com/image.jpg")
    image_base64: Optional[str] = Field(None, description="Base64 图片数据")
    text_query: Optional[str] = Field(None, description="文本查询", example="红烧肉")
    limit: int = Field(default=10, description="返回数量", ge=1, le=50)

    class Config:
        json_schema_extra = {
            "example": {
                "image_url": "https://example.com/image.jpg",
                "image_base64": None,
                "text_query": "红烧肉",
                "limit": 10
            }
        }


class ImageSearchResponse(BaseModel):
    """图片搜索响应."""
    query_type: str = Field(..., description="查询类型", example="image")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="搜索结果列表")

    class Config:
        json_schema_extra = {
            "example": {
                "query_type": "image",
                "results": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "score": 0.95,
                        "payload": {
                            "recipe_name": "红烧肉",
                            "cuisine": "川菜"
                        }
                    }
                ]
            }
        }