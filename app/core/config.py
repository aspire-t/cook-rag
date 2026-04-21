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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例"""
    return Settings()


settings = get_settings()