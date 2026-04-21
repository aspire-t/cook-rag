"""
CookRAG - 企业级菜谱 RAG 系统
FastAPI 应用入口
"""

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager

from loguru import logger

from app.api.routes import api_router
from app.core.config import settings
from app.core.database import engine, Base
from app.core.exceptions import (
    AppException,
    validation_exception_handler,
    http_exception_handler,
    global_exception_handler,
    app_exception_handler,
)
from app.core.metrics import prometheus_middleware, metrics_handler
from app.api.v1.websocket import websocket_endpoint


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting CookRAG API...")

    # 创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("CookRAG API started successfully")

    yield

    # 关闭时
    logger.info("Shutting down CookRAG API...")
    await engine.dispose()
    logger.info("CookRAG API shutdown complete")


# 创建 FastAPI 应用
app = FastAPI(
    title="CookRAG API",
    description="企业级菜谱 RAG 系统 API",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start = time.time()

    response = await call_next(request)

    duration = time.time() - start
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} ({duration:.2f}s)"
    )

    return response


# Prometheus 监控中间件
@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    from app.core.metrics import prometheus_middleware
    return await prometheus_middleware(request, call_next)


# 全局异常处理
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)


# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


# 就绪检查
@app.get("/ready")
async def readiness_check():
    # TODO: 检查数据库、Redis、Qdrant 连接
    return {"status": "ready"}


# Prometheus 指标端点
@app.get("/metrics")
async def metrics():
    """Prometheus 指标采集端点"""
    return metrics_handler(Request(scope={"type": "http"}))


# WebSocket 跟做端点
@app.websocket("/ws/recipes/{recipe_id}/cook")
async def websocket_cook(recipe_id: str, websocket: WebSocket):
    """WebSocket 跟做模式端点"""
    await websocket_endpoint(websocket, recipe_id)


# 注册 API 路由
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )