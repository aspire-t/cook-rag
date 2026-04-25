"""
数据库配置和会话管理
"""

import os
import uuid
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event, TypeDecorator, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB

from app.core.config import settings


class SQLiteUUID(TypeDecorator):
    """SQLite 兼容的 UUID 存储。接受 as_uuid=True 以兼容 pg.UUID 签名。"""
    impl = String(36)
    cache_ok = True

    def __init__(self, as_uuid=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, uuid.UUID):
                return str(value)
            if isinstance(value, str):
                return value
            return str(uuid.UUID(value))
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return uuid.UUID(value)
            except Exception:
                return value
        return None


class SQLiteJSONB(TypeDecorator):
    """SQLite 兼容的 JSONB 存储。"""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and not isinstance(value, str):
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return None


# SQLite 模式下替换 PostgreSQL 类型
if settings.DATABASE_URL.startswith("sqlite"):
    import sqlalchemy.dialects.postgresql as _pg
    _pg.UUID = SQLiteUUID
    _pg.JSONB = SQLiteJSONB


# 创建异步引擎
def create_engine_settings():
    """Create engine with appropriate settings for the database dialect."""
    kwargs = {
        "echo": settings.DEBUG,
    }
    if not settings.DATABASE_URL.startswith("sqlite"):
        kwargs.update({
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20,
        })
    else:
        kwargs["connect_args"] = {"isolation_level": None}
    return create_async_engine(settings.DATABASE_URL, **kwargs)

engine = create_engine_settings()

# 会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Import Base from models (where all models register their tables)
from app.models import Base


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()