"""RAG 上下文管理器 - Redis 会话管理，对话历史维护，多轮对话上下文."""

import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import redis.asyncio as redis

from app.core.config import settings


@dataclass
class Message:
    """对话消息."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None


class ConversationManager:
    """
    会话管理器.

    功能：
    - Redis 会话存储（30 分钟 TTL）
    - 对话历史维护
    - 多轮对话上下文
    - 消息数量限制
    """

    # 会话 TTL（秒）
    SESSION_TTL = 1800  # 30 分钟

    # 最大历史消息数
    MAX_MESSAGES = 20

    # Redis Key 前缀
    SESSION_PREFIX = "cookrag:session"
    HISTORY_PREFIX = "cookrag:history"

    def __init__(self, redis_url: Optional[str] = None):
        """
        初始化会话管理器.

        Args:
            redis_url: Redis URL
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[redis.Redis] = None

    @property
    async def redis(self) -> redis.Redis:
        """获取 Redis 连接（懒加载）."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    def _session_key(self, session_id: str) -> str:
        """生成会话 Key."""
        return f"{self.SESSION_PREFIX}:{session_id}"

    def _history_key(self, session_id: str) -> str:
        """生成历史 Key."""
        return f"{self.HISTORY_PREFIX}:{session_id}"

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话信息.

        Args:
            session_id: 会话 ID

        Returns:
            会话信息
        """
        redis_client = await self.redis
        data = await redis_client.get(self._session_key(session_id))
        if data is None:
            return None
        return json.loads(data)

    async def create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建新会话.

        Args:
            session_id: 会话 ID
            user_id: 用户 ID（可选）

        Returns:
            会话信息
        """
        redis_client = await self.redis

        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "message_count": 0,
        }

        await redis_client.setex(
            self._session_key(session_id),
            self.SESSION_TTL,
            json.dumps(session_data),
        )

        # 初始化空历史列表
        await redis_client.setex(
            self._history_key(session_id),
            self.SESSION_TTL,
            json.dumps([]),
        )

        return session_data

    async def update_session_activity(self, session_id: str) -> bool:
        """
        更新会话活动时间.

        Args:
            session_id: 会话 ID

        Returns:
            True 如果成功
        """
        redis_client = await self.redis
        session_data = await self.get_session(session_id)

        if session_data is None:
            return False

        session_data["last_activity"] = time.time()

        # 刷新 TTL
        await redis_client.setex(
            self._session_key(session_id),
            self.SESSION_TTL,
            json.dumps(session_data),
        )

        # 同时刷新历史 Key 的 TTL
        await redis_client.expire(self._history_key(session_id), self.SESSION_TTL)

        return True

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        添加消息到会话历史.

        Args:
            session_id: 会话 ID
            role: 角色（user/assistant）
            content: 消息内容
            metadata: 元数据

        Returns:
            True 如果成功
        """
        redis_client = await self.redis

        # 检查会话是否存在
        session_data = await self.get_session(session_id)
        if session_data is None:
            # 自动创建会话
            await self.create_session(session_id)

        # 创建消息
        message = Message(
            role=role,
            content=content,
            timestamp=time.time(),
            metadata=metadata,
        )

        # 获取当前历史
        history_data = await redis_client.get(self._history_key(session_id))
        history: List[Dict] = json.loads(history_data) if history_data else []

        # 添加消息
        history.append(asdict(message))

        # 保持最大消息数限制
        if len(history) > self.MAX_MESSAGES:
            history = history[-self.MAX_MESSAGES :]

        # 保存历史
        await redis_client.setex(
            self._history_key(session_id),
            self.SESSION_TTL,
            json.dumps(history),
        )

        # 更新会话活动时间和消息计数
        await self.update_session_activity(session_id)

        # 更新消息计数
        session_data = await self.get_session(session_id)
        if session_data:
            session_data["message_count"] = len(history)
            await redis_client.setex(
                self._session_key(session_id),
                self.SESSION_TTL,
                json.dumps(session_data),
            )

        return True

    async def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[Message]:
        """
        获取会话历史.

        Args:
            session_id: 会话 ID
            limit: 返回消息数量限制

        Returns:
            消息列表（按时间顺序）
        """
        redis_client = await self.redis
        history_data = await redis_client.get(self._history_key(session_id))

        if history_data is None:
            return []

        history: List[Dict] = json.loads(history_data)

        # 应用限制
        if limit:
            history = history[-limit:]

        # 转换为 Message 对象
        return [Message(**msg) for msg in history]

    async def get_context(
        self,
        session_id: str,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        获取对话上下文（用于 RAG）.

        Args:
            session_id: 会话 ID
            max_tokens: 最大 Token 数

        Returns:
            格式化的上下文字符串
        """
        history = await self.get_history(session_id)

        if not history:
            return ""

        # 格式化为对话字符串
        context_lines = []
        for msg in history:
            role_name = "用户" if msg.role == "user" else "助手"
            context_lines.append(f"{role_name}: {msg.content}")

        context = "\n".join(context_lines)

        # 简单 Token 裁剪（按字符数估算）
        if max_tokens and len(context) > max_tokens * 4:  # 粗略估算：1 token ≈ 4 字符
            context = context[-(max_tokens * 4) :]

        return context

    async def clear_history(self, session_id: str) -> bool:
        """
        清空会话历史.

        Args:
            session_id: 会话 ID

        Returns:
            True 如果成功
        """
        redis_client = await self.redis
        await redis_client.delete(self._history_key(session_id))

        # 重置消息计数
        session_data = await self.get_session(session_id)
        if session_data:
            session_data["message_count"] = 0
            await redis_client.setex(
                self._session_key(session_id),
                self.SESSION_TTL,
                json.dumps(session_data),
            )

        return True

    async def delete_session(self, session_id: str) -> bool:
        """
        删除会话.

        Args:
            session_id: 会话 ID

        Returns:
            True 如果成功
        """
        redis_client = await self.redis

        # 删除会话和历史
        await redis_client.delete(self._session_key(session_id))
        await redis_client.delete(self._history_key(session_id))

        return True

    async def close(self):
        """关闭 Redis 连接."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# 全局单例
_conversation_manager: Optional[ConversationManager] = None


def get_conversation_manager() -> ConversationManager:
    """获取会话管理器实例."""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager


async def get_or_create_session(
    session_id: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    获取或创建会话.

    Args:
        session_id: 会话 ID
        user_id: 用户 ID

    Returns:
        会话信息
    """
    manager = get_conversation_manager()
    session = await manager.get_session(session_id)
    if session is None:
        session = await manager.create_session(session_id, user_id)
    return session


async def add_conversation_message(
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    添加对话消息.

    Args:
        session_id: 会话 ID
        role: 角色
        content: 内容
        metadata: 元数据

    Returns:
        True 如果成功
    """
    manager = get_conversation_manager()
    return await manager.add_message(session_id, role, content, metadata)


async def get_conversation_history(
    session_id: str,
    limit: Optional[int] = 10,
) -> List[Dict[str, Any]]:
    """
    获取对话历史.

    Args:
        session_id: 会话 ID
        limit: 限制数量

    Returns:
        历史消息列表
    """
    manager = get_conversation_manager()
    messages = await manager.get_history(session_id, limit)
    return [asdict(msg) for msg in messages]
