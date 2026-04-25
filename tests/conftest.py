"""pytest 配置."""

import os
import pytest


# Set SQLite mode BEFORE any app imports
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./cookrag.db")
os.environ.setdefault("SKIP_DB_CREATE", "true")
os.environ.setdefault("ENABLE_EMBEDDING", "false")
os.environ.setdefault("ENABLE_RERANK", "false")
os.environ.setdefault("ENABLE_CLIP", "false")


# Patch PostgreSQL types before model imports
import sqlalchemy
from sqlalchemy.types import String, TypeDecorator
import json


class SQLiteUUID(TypeDecorator):
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        import uuid
        if value is not None:
            if isinstance(value, uuid.UUID):
                return str(value)
            if isinstance(value, str):
                return value
            return str(uuid.UUID(value))
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            import uuid
            try:
                return uuid.UUID(value)
            except Exception:
                return value
        return None


class SQLiteJSONB(TypeDecorator):
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


import sqlalchemy.dialects.postgresql as pg
pg.UUID = SQLiteUUID
pg.JSONB = SQLiteJSONB


@pytest.fixture(scope="session")
def event_loop_policy():
    """使用默认的事件循环策略."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()
