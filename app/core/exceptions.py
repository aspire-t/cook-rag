"""
全局异常处理和错误码体系.

错误码规范:
- 1xxx: 认证相关错误
- 2xxx: 通用/系统错误
- 3xxx: 搜索/RAG 相关错误
- 4xxx: 菜谱/UGC 相关错误
- 5xxx: 举报/审核相关错误
"""

from typing import Any, Optional
from fastapi import HTTPException, status


# ============== 错误码常量 ==============

# 1xxx: 认证相关
ERROR_AUTH_INVALID_TOKEN = 1001
ERROR_AUTH_TOKEN_EXPIRED = 1002
ERROR_AUTH_MISSING_TOKEN = 1003
ERROR_AUTH_INVALID_CREDENTIALS = 1004
ERROR_AUTH_USER_NOT_FOUND = 1005
ERROR_AUTH_PERMISSION_DENIED = 1006

# 2xxx: 通用/系统错误
ERROR_INTERNAL = 2001
ERROR_BAD_REQUEST = 2002
ERROR_NOT_FOUND = 2003
ERROR_SERVICE_UNAVAILABLE = 2004
ERROR_RATE_LIMIT_EXCEEDED = 2005
ERROR_VALIDATION_ERROR = 2006

# 3xxx: 搜索/RAG 相关
ERROR_SEARCH_FAILED = 3001
ERROR_RAG_FAILED = 3002
ERROR_CACHE_FAILED = 3003

# 4xxx: 菜谱/UGC 相关
ERROR_RECIPE_NOT_FOUND = 4001
ERROR_RECIPE_ALREADY_FAVORITED = 4002
ERROR_RECIPE_UPLOAD_FAILED = 4003
ERROR_RECIPE_MARKDOWN_PARSE_FAILED = 4004
ERROR_RECIPE_FILE_TOO_LARGE = 4005

# 5xxx: 举报/审核相关
ERROR_REPORT_ALREADY_SUBMITTED = 5001
ERROR_REPORT_FAILED = 5002
ERROR_RECIPE_OFFLINE = 5003


# ============== 错误码映射 ==============

ERROR_MESSAGES = {
    # 认证相关
    ERROR_AUTH_INVALID_TOKEN: "无效的 Token",
    ERROR_AUTH_TOKEN_EXPIRED: "Token 已过期",
    ERROR_AUTH_MISSING_TOKEN: "缺少认证 Token",
    ERROR_AUTH_INVALID_CREDENTIALS: "用户名或密码错误",
    ERROR_AUTH_USER_NOT_FOUND: "用户不存在",
    ERROR_AUTH_PERMISSION_DENIED: "权限不足",
    # 通用/系统
    ERROR_INTERNAL: "内部服务器错误",
    ERROR_BAD_REQUEST: "请求参数错误",
    ERROR_NOT_FOUND: "资源不存在",
    ERROR_SERVICE_UNAVAILABLE: "服务暂时不可用",
    ERROR_RATE_LIMIT_EXCEEDED: "请求频率超限",
    ERROR_VALIDATION_ERROR: "数据验证失败",
    # 搜索/RAG
    ERROR_SEARCH_FAILED: "搜索失败",
    ERROR_RAG_FAILED: "RAG 处理失败",
    ERROR_CACHE_FAILED: "缓存操作失败",
    # 菜谱/UGC
    ERROR_RECIPE_NOT_FOUND: "菜谱不存在",
    ERROR_RECIPE_ALREADY_FAVORITED: "已收藏该菜谱",
    ERROR_RECIPE_UPLOAD_FAILED: "菜谱上传失败",
    ERROR_RECIPE_MARKDOWN_PARSE_FAILED: "Markdown 解析失败",
    ERROR_RECIPE_FILE_TOO_LARGE: "文件大小超限",
    # 举报/审核
    ERROR_REPORT_ALREADY_SUBMITTED: "已举报过该菜谱",
    ERROR_REPORT_FAILED: "举报失败",
    ERROR_RECIPE_OFFLINE: "菜谱已下架",
}


# ============== 业务异常类 ==============

class AppException(Exception):
    """应用业务异常基类."""

    def __init__(
        self,
        error_code: int,
        message: Optional[str] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        data: Optional[Any] = None,
    ):
        self.error_code = error_code
        self.message = message or ERROR_MESSAGES.get(error_code, "未知错误")
        self.status_code = status_code
        self.data = data
        super().__init__(self.message)


class AuthenticationException(AppException):
    """认证异常."""

    def __init__(self, error_code: int = ERROR_AUTH_INVALID_TOKEN, message: Optional[str] = None):
        super().__init__(error_code=error_code, message=message, status_code=status.HTTP_401_UNAUTHORIZED)


class PermissionDeniedException(AppException):
    """权限异常."""

    def __init__(self, message: str = "权限不足"):
        super().__init__(
            error_code=ERROR_AUTH_PERMISSION_DENIED,
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class NotFoundException(AppException):
    """资源不存在异常."""

    def __init__(self, error_code: int = ERROR_NOT_FOUND, message: Optional[str] = None):
        super().__init__(error_code=error_code, message=message, status_code=status.HTTP_404_NOT_FOUND)


class RateLimitException(AppException):
    """限流异常."""

    def __init__(self, message: str = "请求频率超限"):
        super().__init__(
            error_code=ERROR_RATE_LIMIT_EXCEEDED,
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class RecipeException(AppException):
    """菜谱业务异常."""

    def __init__(self, error_code: int, message: Optional[str] = None):
        super().__init__(error_code=error_code, message=message, status_code=status.HTTP_400_BAD_REQUEST)


class ReportException(AppException):
    """举报业务异常."""

    def __init__(self, error_code: int, message: Optional[str] = None):
        super().__init__(error_code=error_code, message=message, status_code=status.HTTP_400_BAD_REQUEST)


# ============== FastAPI 异常处理器 ==============

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from loguru import logger


async def app_exception_handler(request: Request, exc: AppException):
    """处理 AppException."""
    logger.warning(f"AppException: {exc.error_code} - {exc.message} - {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.error_code,
            "message": exc.message,
            "data": exc.data,
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求参数验证异常."""
    logger.warning(f"Validation error: {exc.errors()} - {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": ERROR_VALIDATION_ERROR,
            "message": "请求参数验证失败",
            "data": {"errors": exc.errors()},
        },
    )


async def pydantic_exception_handler(request: Request, exc: ValidationError):
    """处理 Pydantic 验证异常."""
    logger.warning(f"Pydantic validation error: {exc} - {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "code": ERROR_VALIDATION_ERROR,
            "message": "数据格式验证失败",
            "data": {"errors": exc.errors()},
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """处理 FastAPI HTTPException."""
    logger.warning(f"HTTPException: {exc.status_code} - {exc.detail} - {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": ERROR_INTERNAL if exc.status_code >= 500 else ERROR_BAD_REQUEST,
            "message": exc.detail,
        },
    )


async def global_exception_handler(request: Request, exc: Exception):
    """处理未捕获的异常."""
    logger.exception(f"Unhandled exception: {exc} - {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": ERROR_INTERNAL,
            "message": "内部服务器错误",
            "data": None,
        },
    )
