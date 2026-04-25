"""
CookRAG 应用配置
"""

from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    # 环境
    DEBUG: bool = True
    ENV: str = "development"

    # 应用
    APP_NAME: str = "CookRAG"
    API_VERSION: str = "v1"

    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://cookrag:password@localhost:5432/cookrag"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "recipes"

    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ES_INDEX_NAME: str = "recipes"

    # 通义千问 API
    DASHSCOPE_API_KEY: str = ""
    LLM_MODEL: str = "qwen-plus"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # 2 小时
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 天

    # 微信小程序配置
    WECHAT_APPID: str = ""
    WECHAT_SECRET: str = ""
    WECHAT_GRANT_TYPE: str = "authorization_code"

    # 文件上传
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # 限流配置
    RATE_LIMIT_DEFAULT: int = 100  # 默认 100 次/分钟
    RATE_LIMIT_SEARCH: int = 30  # 搜索 API：30 次/分钟
    RATE_LIMIT_LLM: int = 10  # LLM API：10 次/分钟
    RATE_LIMIT_AUTH: int = 5  # 认证 API：5 次/分钟
    RATE_LIMIT_UPLOAD: int = 20  # 上传 API：20 次/分钟

    # Prompt 配置
    PROMPT_DIR: str = "app/prompts"
    MAX_CONTEXT_TOKENS: int = 4096  # 最大上下文 Token 数

    # 会话配置
    SESSION_TTL: int = 1800  # 30 分钟
    MAX_CONVERSATION_HISTORY: int = 20  # 最大历史消息数

    # Image Storage
    HOWTOCOOK_IMAGE_BASE_URL: str = "https://king-jingxiang.github.io/HowToCook/images/dishes/"
    IMAGE_FALLBACK_BASE: str = "/howtocook-images/dishes/"  # local static mount fallback
    IMAGE_REPO_NAME: str = "cook-rag-images"  # GitHub 图片仓库名
    IMAGE_REPO_OWNER: str = "aspire-t"  # GitHub 用户名
    IMAGE_BASE_CDN_URL: str = "https://cdn.jsdelivr.net/gh/aspire-t/cook-rag-images@main/"

    # CLIP Model
    CLIP_MODEL_NAME: str = "OFA-Sys/chinese-clip-vit-base-patch16"
    CLIP_DEVICE: str = "mps"  # mps/cuda/cpu

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例"""
    return Settings()


settings = get_settings()