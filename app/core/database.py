"""
数据库配置和会话管理
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event

from app.core.config import settings


# 创建异步引擎
def create_engine_settings():
    """Create engine with appropriate settings for the database dialect."""
    kwargs = {
        "echo": settings.DEBUG,
    }
    # SQLite doesn't support pool_size/max_overflow
    if not settings.DATABASE_URL.startswith("sqlite"):
        kwargs.update({
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20,
        })
    else:
        # Disable foreign key checks for SQLite during table creation
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

# Base 类
Base = declarative_base()


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()