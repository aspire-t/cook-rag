"""
API 路由注册
"""

from fastapi import APIRouter

from app.api.v1 import search, recipes, users, upload, report, enterprise, standardize, inventory


api_router = APIRouter()

# 注册子路由
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(report.router, prefix="/report", tags=["report"])
api_router.include_router(enterprise.router, prefix="/enterprise", tags=["enterprise"])
api_router.include_router(standardize.router, prefix="/standardize", tags=["standardize"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])