"""
WebSocket 跟做模式.

功能:
- 实时步骤推送
- 倒计时定时器
- 语音交互支持（后续迭代）
- 跟做进度跟踪
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.recipe import Recipe
from app.models.step import RecipeStep
from loguru import logger


class ConnectionManager:
    """WebSocket 连接管理器."""

    def __init__(self):
        # recipe_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # recipe_id -> 跟做状态
        self.cooking_sessions: Dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, recipe_id: str):
        """接受 WebSocket 连接."""
        await websocket.accept()
        if recipe_id not in self.active_connections:
            self.active_connections[recipe_id] = set()
        self.active_connections[recipe_id].add(websocket)
        logger.info(f"WebSocket connected: recipe_id={recipe_id}, total_connections={len(self.active_connections[recipe_id])}")

    def disconnect(self, websocket: WebSocket, recipe_id: str):
        """断开 WebSocket 连接."""
        if recipe_id in self.active_connections:
            self.active_connections[recipe_id].discard(websocket)
            if not self.active_connections[recipe_id]:
                del self.active_connections[recipe_id]
                # 清理跟做会话
                if recipe_id in self.cooking_sessions:
                    del self.cooking_sessions[recipe_id]
        logger.info(f"WebSocket disconnected: recipe_id={recipe_id}")

    async def broadcast_to_recipe(self, recipe_id: str, message: dict):
        """向指定菜谱的所有连接广播消息."""
        if recipe_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[recipe_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)
            # 清理断开的连接
            for conn in disconnected:
                self.disconnect(conn, recipe_id)

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """发送个人消息."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")

    def create_cooking_session(self, recipe_id: str, user_id: str) -> dict:
        """创建跟做会话."""
        session = {
            "recipe_id": recipe_id,
            "user_id": user_id,
            "current_step": 0,
            "started_at": datetime.now().isoformat(),
            "paused": False,
            "timer_remaining": 0,  # 剩余时间（秒）
            "completed_steps": [],
        }
        self.cooking_sessions[recipe_id] = session
        return session

    def get_cooking_session(self, recipe_id: str) -> Optional[dict]:
        """获取跟做会话."""
        return self.cooking_sessions.get(recipe_id)

    def update_cooking_session(self, recipe_id: str, **kwargs):
        """更新跟做会话."""
        if recipe_id in self.cooking_sessions:
            self.cooking_sessions[recipe_id].update(kwargs)


# 全局连接管理器
manager = ConnectionManager()


async def get_recipe_steps(db: AsyncSession, recipe_id: str) -> list:
    """获取菜谱步骤列表."""
    result = await db.execute(
        select(RecipeStep)
        .where(RecipeStep.recipe_id == recipe_id)
        .order_by(RecipeStep.step_number)
    )
    steps = result.scalars().all()
    return [
        {
            "step_number": step.step_number,
            "description": step.description,
            "duration_seconds": getattr(step, "duration_seconds", None),
        }
        for step in steps
    ]


async def countdown_timer(manager: ConnectionManager, recipe_id: str, seconds: int):
    """倒计时定时器."""
    session = manager.get_cooking_session(recipe_id)
    if not session:
        return

    for remaining in range(seconds, 0, -1):
        session["timer_remaining"] = remaining
        await manager.broadcast_to_recipe(
            recipe_id,
            {
                "type": "timer_update",
                "data": {
                    "remaining_seconds": remaining,
                    "formatted": format_time(remaining),
                },
            },
        )
        await asyncio.sleep(1)

        # 检查会话是否还存在
        if not manager.get_cooking_session(recipe_id):
            break

    # 倒计时结束
    if manager.get_cooking_session(recipe_id):
        session["timer_remaining"] = 0
        await manager.broadcast_to_recipe(
            recipe_id,
            {
                "type": "timer_complete",
                "data": {"message": "计时完成"},
            },
        )


def format_time(seconds: int) -> str:
    """格式化时间为 MM:SS."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


async def websocket_endpoint(
    websocket: WebSocket,
    recipe_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket 跟做端点.

    支持的操作:
    - start: 开始跟做
    - next: 下一步
    - prev: 上一步
    - pause: 暂停
    - resume: 继续
    - timer_start: 开始倒计时
    - timer_stop: 停止倒计时
    - status: 获取当前状态
    """
    # 验证菜谱是否存在
    result = await db.execute(
        select(Recipe).where(Recipe.id == recipe_id)
    )
    recipe = result.scalar_one_or_none()

    if not recipe:
        await websocket.close(code=4004, reason="菜谱不存在")
        return

    # 连接 WebSocket
    await manager.connect(websocket, recipe_id)

    # 获取步骤列表
    steps = await get_recipe_steps(db, recipe_id)

    # 发送初始消息
    await manager.send_personal_message(
        websocket,
        {
            "type": "connected",
            "data": {
                "recipe_id": str(recipe_id),
                "recipe_name": recipe.name,
                "total_steps": len(steps),
                "steps": steps,
            },
        },
    )

    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            # 获取或创建跟做会话
            session = manager.get_cooking_session(recipe_id)
            if not session:
                session = manager.create_cooking_session(recipe_id, str(recipe_id))

            # 处理不同类型的消息
            if msg_type == "start":
                # 开始跟做
                session["current_step"] = 0
                session["paused"] = False
                session["completed_steps"] = []
                await manager.broadcast_to_recipe(
                    recipe_id,
                    {
                        "type": "step_update",
                        "data": {
                            "current_step": 0,
                            "step": steps[0] if steps else None,
                            "progress": f"0/{len(steps)}",
                        },
                    },
                )

            elif msg_type == "next":
                # 下一步
                current = session["current_step"]
                if current < len(steps) - 1:
                    session["current_step"] = current + 1
                    session["completed_steps"].append(current)
                    await manager.broadcast_to_recipe(
                        recipe_id,
                        {
                            "type": "step_update",
                            "data": {
                                "current_step": current + 1,
                                "step": steps[current + 1] if current + 1 < len(steps) else None,
                                "progress": f"{current + 1}/{len(steps)}",
                            },
                        },
                    )

            elif msg_type == "prev":
                # 上一步
                if session["current_step"] > 0:
                    session["current_step"] -= 1
                    if session["completed_steps"] and session["completed_steps"][-1] == session["current_step"]:
                        session["completed_steps"].pop()
                    await manager.broadcast_to_recipe(
                        recipe_id,
                        {
                            "type": "step_update",
                            "data": {
                                "current_step": session["current_step"],
                                "step": steps[session["current_step"]],
                                "progress": f"{session['current_step']}/{len(steps)}",
                            },
                        },
                    )

            elif msg_type == "pause":
                # 暂停
                session["paused"] = True
                await manager.broadcast_to_recipe(
                    recipe_id,
                    {"type": "pause", "data": {"message": "跟做已暂停"}},
                )

            elif msg_type == "resume":
                # 继续
                session["paused"] = False
                await manager.broadcast_to_recipe(
                    recipe_id,
                    {"type": "resume", "data": {"message": "跟做已继续"}},
                )

            elif msg_type == "timer_start":
                # 开始倒计时
                duration = message.get("duration", 60)  # 默认 60 秒
                asyncio.create_task(countdown_timer(manager, recipe_id, duration))

            elif msg_type == "timer_stop":
                # 停止倒计时
                session["timer_remaining"] = 0
                await manager.broadcast_to_recipe(
                    recipe_id,
                    {"type": "timer_stop", "data": {"message": "计时已停止"}},
                )

            elif msg_type == "status":
                # 获取当前状态
                await manager.send_personal_message(
                    websocket,
                    {
                        "type": "status",
                        "data": {
                            "current_step": session["current_step"],
                            "paused": session["paused"],
                            "timer_remaining": session["timer_remaining"],
                            "completed_steps": session["completed_steps"],
                            "progress": f"{session['current_step']}/{len(steps)}",
                        },
                    },
                )

            elif msg_type == "complete":
                # 完成跟做
                session["current_step"] = len(steps)
                await manager.broadcast_to_recipe(
                    recipe_id,
                    {
                        "type": "complete",
                        "data": {
                            "message": "恭喜完成！",
                            "total_steps": len(steps),
                            "completed_at": datetime.now().isoformat(),
                        },
                    },
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket, recipe_id)
        logger.info(f"WebSocket disconnected: recipe_id={recipe_id}")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        manager.disconnect(websocket, recipe_id)
