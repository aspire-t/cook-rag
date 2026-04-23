"""pytest 配置."""

import pytest


@pytest.fixture(scope="session")
def event_loop_policy():
    """使用默认的事件循环策略."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()
