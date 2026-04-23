"""
API 路由注册
"""

from fastapi import APIRouter

from app.api.v1 import search, recipes, users, upload, report, images


api_router = APIRouter()

# 注册子路由
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(report.router, prefix="/report", tags=["report"])
api_router.include_router(images.router, tags=["images"])